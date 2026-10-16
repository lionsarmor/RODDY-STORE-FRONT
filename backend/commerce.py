"""Durable mixed-cart quotes, inventory reservations and fulfillment outbox.

Only the single-process worker submits supplier orders. A submission with an
unknown outcome is reconciled by external reference, never blindly repeated.
"""
import json
import re
import secrets
import threading
import time
from uuid import UUID

from fastapi import HTTPException

from .printify import PrintifyUnavailable
from .square import PaymentUnavailable
from .keycaps import selection_input, snapshot, label
from .order_records import OrderRecords
from .fulfillment_holds import FulfillmentHolds
from .mouser_orders import MouserUnavailable, MouserCostChanged
from .pricing import Pricing


def cents(value):
    if type(value) not in (int, float) or not 0 <= value <= 999999:
        raise HTTPException(409, "Invalid price or shipping rate.")
    result = round(value * 100)
    if abs(value * 100 - result) > .00001:
        raise HTTPException(409, "Prices must have at most two decimal places.")
    return result


def address_input(raw):
    if not isinstance(raw, dict):
        raise HTTPException(400, "Enter your shipping address.")
    result = {}
    for key, limit in {"first_name": 80, "last_name": 80, "email": 254, "phone": 30,
                       "country": 2, "region": 2, "address1": 150, "address2": 150,
                       "city": 100, "zip": 12}.items():
        value = raw.get(key, "")
        if not isinstance(value, str) or len(value.strip()) > limit or any(ord(c) < 32 for c in value):
            raise HTTPException(400, "Check your shipping address fields.")
        result[key] = value.strip()
    result["country"] = result["country"].upper()
    result["region"] = result["region"].upper()
    if (any(not result[k] for k in result if k != "address2")
            or result["country"] not in {"US", "CA"}
            or not re.fullmatch(r"[A-Z]{2}", result["region"])
            or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", result["email"])
            or len(re.sub(r"\D", "", result["phone"])) < 7
            or not re.fullmatch(r"\d{5}(?:-\d{4})?" if result["country"] == "US" else r"[A-Za-z]\d[A-Za-z] ?\d[A-Za-z]\d", result["zip"])):
        raise HTTPException(400, "Enter a complete US or Canadian address, email and phone number.")
    regions = {"US": set("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY AS GU MP PR VI AA AE AP".split()),
               "CA": set("AB BC MB NB NL NS NT NU ON PE QC SK YT".split())}
    if result["region"] not in regions[result["country"]]:
        raise HTTPException(400, "Enter a valid state or province abbreviation.")
    return result


def cart_input(raw):
    if not isinstance(raw, list) or not 1 <= len(raw) <= 30:
        raise HTTPException(400, "Choose between one and 30 items.")
    result, seen = [], set()
    for item in raw:
        if not isinstance(item, dict):
            raise HTTPException(400, "Invalid cart item.")
        pid, vid, qty = item.get("id"), item.get("variantId", ""), item.get("qty")
        design = selection_input(item['design']) if 'design' in item else None
        selection_key = json.dumps(design, sort_keys=True) if design else ''
        if (not isinstance(pid, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,100}", pid)
                or not isinstance(vid, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{0,80}", vid)
                or type(qty) is not int or not 1 <= qty <= 99 or (pid, vid, selection_key) in seen):
            raise HTTPException(400, "Invalid cart quantities or duplicate selections.")
        seen.add((pid, vid, selection_key))
        result.append({"id": pid, "variantId": vid, "qty": qty, **({"design": design} if design else {})})
    return json.dumps(sorted(result, key=lambda i: (i["id"], i["variantId"], json.dumps(i.get("design"), sort_keys=True))), sort_keys=True)


class Commerce:
    def __init__(self, connect, catalog, digital_items, provider, printify, enabled, packets=None):
        self.connect, self.catalog, self.digital_items = connect, catalog, digital_items
        self.provider, self.printify, self.enabled = provider, printify, enabled
        self.packets = packets
        self.supplier_quote_factory = None
        self.mouser_factory = None
        self.holds = FulfillmentHolds(connect)
        self.pricing = Pricing(connect)
        self.lock = threading.Lock()
        self.recover = lambda order: None
        self.records = OrderRecords(connect)
        with connect() as db:
            columns = {r[1] for r in db.execute("PRAGMA table_info(orders)")}
            for name, kind in {"address": "TEXT", "shipping": "INTEGER NOT NULL DEFAULT 0",
                               "quote_id": "TEXT", "link_id": "TEXT", "checked": "INTEGER NOT NULL DEFAULT 0", "cancelled": "INTEGER NOT NULL DEFAULT 0"}.items():
                if name not in columns:
                    db.execute(f"ALTER TABLE orders ADD COLUMN {name} {kind}")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS quotes (
              id TEXT PRIMARY KEY, cart TEXT NOT NULL, items TEXT NOT NULL,
              address TEXT, shipping INTEGER NOT NULL, created INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS inventory (product TEXT PRIMARY KEY, stock INTEGER NOT NULL CHECK(stock>=0));
            CREATE TABLE IF NOT EXISTS reservations (
              session TEXT NOT NULL REFERENCES orders(session), product TEXT NOT NULL,
              qty INTEGER NOT NULL, PRIMARY KEY(session,product)
            );
            CREATE TABLE IF NOT EXISTS sale_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, session TEXT NOT NULL UNIQUE REFERENCES orders(session),
              confirmed INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS fulfillments (
              session TEXT NOT NULL REFERENCES orders(session), kind TEXT NOT NULL,
              state TEXT NOT NULL, supplier_id TEXT, error TEXT NOT NULL DEFAULT '',
              shipments TEXT NOT NULL DEFAULT '[]', updated INTEGER NOT NULL,
              PRIMARY KEY(session,kind)
            );
            """)

    def check_payment(self, order):
        if not order.get('provider_id'):
            return False
        if hasattr(self.provider, 'payment_report'):
            report = self.provider.payment_report(order['provider_id'], order['amount'])
            if order.get('cancelled') and not report.get('captured'):report['status']='canceled'
            self.records.record(order, report)
            return report['fullyPaid']
        return self.provider.paid(order['provider_id'], order['amount'])

    def inventory(self):
        products = [p for p in self.catalog()["products"] if p.get("type") == "physical" and not p.get("merch") and not p.get("keycaps") and (not p.get("supplier") or p["supplier"].get("fulfillment")=="office")]
        with self.connect() as db:
            for p in products:
                db.execute("INSERT OR IGNORE INTO inventory VALUES(?,?)", (p["id"], max(0, int(p.get("stock", 0)))))
            stock = {r["product"]: r["stock"] for r in db.execute("SELECT * FROM inventory")}
            held = {r["product"]: r["qty"] for r in db.execute("SELECT product,SUM(qty) qty FROM reservations GROUP BY product")}
        return [{"id": p["id"], "name": p["name"], "stock": stock[p["id"]],
                 "reserved": held.get(p["id"], 0), "available": stock[p["id"]] - held.get(p["id"], 0)} for p in products]

    def price(self, cart, live=False, country=None):
        self.holds.check(json.loads(cart))
        catalog = self.catalog()
        products = {p["id"]: p for p in catalog["products"]}
        result, supplier, product_cache = [], None, {}
        for line in json.loads(cart):
            p = products.get(line["id"])
            if (not p or not p.get("active") or p.get("status") != "available" or p.get("pricePending")
                    or p.get("downloadUrl") or "free" in p.get("tags", [])):
                raise HTTPException(409, "An item is unavailable. Refresh your cart.")
            if line.get("design") and not p.get("keycaps"):
                raise HTTPException(400, "This product does not accept a keycap design.")
            if country and p.get('type') == 'physical' and 'shippingCountries' in p and country not in p['shippingCountries']:
                raise HTTPException(409, 'This item does not ship to the selected country.')
            if p.get("supplier") and (not isinstance(p["supplier"], dict) or p["supplier"].get("fulfillment") not in {"office","manual","automatic"} or p.get("merch") or p["supplier"].get("provider") not in {"mouser", "aliexpress"}):
                raise HTTPException(409, "This item is temporarily unavailable. Please contact RODDY.")
            if (p.get('supplier') or {}).get('fulfillment')=='automatic' and p['supplier']['provider']!='mouser':
                raise HTTPException(409,'Automatic fulfillment is not connected for this item.')
            item = {"id": p["id"], "name": p["name"], "qty": line["qty"], "variantId": line["variantId"]}
            if self.pricing.applies(p):
                item.update(pricingRevision=self.pricing.settings()['revision'],pricingFloorCents=cents(p.get('pricingFloor',0)))
            if p.get("type") == "digital":
                if line["qty"] != 1 or line["variantId"]:
                    raise HTTPException(400, "Digital downloads allow one copy per order.")
                item.update(self.digital_items(json.dumps([p["id"]]))[0], kind="digital", qty=1)
            elif p.get('type')=='physical' and (p.get('supplier') or {}).get('fulfillment') in {'manual','automatic'}:
                if not self.enabled or self.provider.mode!='live' or p['supplier']['provider'] not in {'aliexpress','mouser'} or p.get('trackStock') is not False or not self.supplier_quote_factory:
                    raise HTTPException(409,'This item is temporarily unavailable.')
                item.update(kind=p['supplier']['provider'],cents=cents(p['price']),supplier=dict(p['supplier']),label='',officeShipping=p.get('officeShipping',{}))
            elif p.get("type") == "physical" and p.get("keycaps"):
                if not self.enabled or self.provider.mode != "live" or p.get("merch") or p.get("supplier") or p.get("trackStock") is not False or line["variantId"]:
                    raise HTTPException(409, "Custom keycap fulfillment is not configured for this product.")
                design = snapshot(catalog, p, line.get("design"))
                item.update(kind="keycaps", cents=cents(p["price"]), designSnapshot=design,
                            label=label(design["selection"]), officeShipping=p.get("officeShipping", {}))
            elif p.get("type") == "physical" and p.get("merch"):
                if not self.enabled or self.provider.mode != "live":
                    raise HTTPException(503, "Made-to-order checkout is unavailable.")
                m = p["merch"]
                v = next((v for v in m["variants"] if v["id"] == line["variantId"]), None)
                if not v or not v.get("enabled") or (v.get("available") is not True and 'pricingRevision' not in item) or (country and country not in m.get("shippingCountries", [])):
                    raise HTTPException(409, "This color, size or shipping country is unavailable.")
                item.update(kind="printify", cents=cents(v["price"]), product_id=m["productId"],
                            variant_id=v["providerVariantId"], shop_id=m["shopId"], label=" / ".join(filter(None, [v.get("color"), v.get("size")])))
                if live:
                    supplier = supplier or self.printify()
                    if not supplier or supplier.shop_id != m.get("shopId"):
                        raise HTTPException(503, "Merchandise fulfillment is not connected.")
                    if m["productId"] not in product_cache:
                        product_cache[m["productId"]] = supplier.product(m["productId"])
                    product = product_cache[m["productId"]]
                    actual = next((v for v in product["variants"] if v["id"] == item["variant_id"]), None)
                    if not actual or not actual["enabled"] or actual["available"] is not True:
                        raise HTTPException(409, "This selection just became unavailable. Choose another option.")
                    if type(actual.get("costCents")) is not int or ('pricingRevision' not in item and actual["costCents"] >= item["cents"]):
                        if type(actual.get('costCents')) is int:
                            self.holds.suspend([item],'Printify unit cost meets or exceeds the retail price. Update pricing before clearing this hold.')
                        raise HTTPException(409, "This selection needs a price update before it can be purchased.")
            elif p.get("type") == "physical":
                if not self.enabled or p.get("trackStock") is not True or line["variantId"]:
                    raise HTTPException(409, "Office-shipped products need tracked inventory before checkout.")
                item.update(kind="office", cents=cents(p["price"]), officeShipping=p.get("officeShipping", {}))
            else:
                raise HTTPException(409, "Unsupported product type.")
            if item["cents"] <= 0:
                raise HTTPException(409, "Get free downloads from their product pages.")
            result.append(item)
        if sum(i["qty"] * i["cents"] for i in result) > 99999999:
            raise HTTPException(400, "Order total is too large.")
        return result, supplier

    @staticmethod
    def automatic_mouser(items):
        return [i for i in items if i.get('kind')=='mouser' and i.get('supplier',{}).get('fulfillment')=='automatic']

    def mouser_quote(self,items,address,snapshot=None):
        try:
            client=self.mouser_factory()
            def reprice(items,total,shipping,goods):
                calculated=self.pricing.reprice(items,total,shipping,goods)
                return [price if 'pricingRevision' in item else item['cents'] for item,price in zip(items,calculated)]
            result=client.preview(snapshot,items,address) if snapshot else client.quote(items,address,pricing=reprice if any('pricingRevision' in i for i in items) else None)
            if snapshot and result['totalCents']>snapshot['totalCents']:
                raise MouserCostChanged('Mouser cost increased above the accepted quote. Review pricing before fulfilling.')
            return result
        except MouserCostChanged as exc:
            self.holds.suspend(items,str(exc))
            raise HTTPException(409,'An item needs a price review and has been temporarily suspended.') from None
        except (MouserUnavailable,KeyError,TypeError,ValueError,AttributeError):
            raise HTTPException(409,'Live fulfillment is unavailable for this selection. Please try again later or contact RODDY.') from None

    @staticmethod
    def supplier_lines(items):
        return [{"product_id": i["product_id"], "variant_id": i["variant_id"], "quantity": i["qty"],
                 "external_id": i["id"] + ":" + i["variantId"]} for i in items if i.get("kind") == "printify"]

    def quote(self, body):
        cart = cart_input(body.get("items"))
        items, _ = self.price(cart)
        physical = any(i["kind"] != "digital" for i in items)
        address = address_input(body.get("address")) if physical else None
        items, supplier = self.price(cart, live=physical, country=address["country"] if physical else None)
        office_shipping = 0
        available = {i["id"]: i["available"] for i in self.inventory()} if any(i["kind"] == "office" for i in items) else {}
        shipping_groups = {}
        for i in items:
            if i["kind"] in {"office", "keycaps"}:
                group = shipping_groups.setdefault(i["id"], {**i, "qty": 0})
                group["qty"] += i["qty"]
        for i in shipping_groups.values():
            if i["kind"] == "office" and i["qty"] > available.get(i["id"], 0):
                raise HTTPException(409, "There is not enough office stock for this order.")
            rate = i["officeShipping"].get(address["country"])
            if not isinstance(rate, dict) or any(k not in rate for k in ["firstItem", "additionalItem"]):
                raise HTTPException(409, "Shipping is not configured for this product and country.")
            office_shipping += cents(rate["firstItem"]) + cents(rate["additionalItem"]) * (i["qty"] - 1)
        direct_shipping=0
        automatic=self.automatic_mouser(items)
        if automatic:
            if any(i['kind']=='mouser' and i not in automatic for i in items):raise HTTPException(409,'Please order these supplier items separately.')
            procurement=self.mouser_quote(automatic,address)
            for item in automatic:item['procurement']=procurement
            direct_shipping+=procurement['shippingCents']
        for item in items:
            if item['kind'] in {'aliexpress','mouser'} and item not in automatic:
                item['procurement']=self.supplier_quote_factory(item['kind']).quote(item,address)
                direct_shipping+=item['procurement']['shippingCents']
        pod_shipping = supplier.quote_shipping(self.supplier_lines(items), address) if supplier else 0
        pod=[i for i in items if i['kind']=='printify']
        if any('pricingRevision' in i for i in pod):
            rules=self.pricing.settings();quantities=sum(i['qty'] for i in pod)
            for item in pod:
                if 'pricingRevision' not in item:continue
                actual=next((v for v in supplier.product(item['product_id'])['variants'] if v['id']==item['variant_id']),{})
                cost=actual.get('costCents')
                if type(cost) is not int:raise HTTPException(409,'A current price is unavailable.')
                shipping_share=pod_shipping/quantities
                landed=(cost+shipping_share)*(1+rules['unknownTaxPercent']/100)
                item['cents']=self.pricing.retail(landed,shipping_share,item['pricingFloorCents'],rules)
        for item in items:
            if item['kind']=='printify':item['procurement']={'shippingCents':pod_shipping,'automatic':True}
        shipping = office_shipping + pod_shipping + direct_shipping
        quote_id, now = secrets.token_urlsafe(32), int(time.time())
        with self.connect() as db:
            db.execute("DELETE FROM quotes WHERE created < ?", (now - 86400,))
            db.execute("INSERT INTO quotes VALUES(?,?,?,?,?,?)", (quote_id, cart, json.dumps(items), json.dumps(address), shipping, now))
        subtotal = sum(i["cents"] * i["qty"] for i in items)
        return {"quoteId": quote_id, "subtotal": subtotal, "shipping": shipping, "amountTotal": subtotal + shipping,
                'items':[{'id':i['id'],'variantId':i['variantId'],'qty':i['qty'],'unitPriceCents':i['cents']} for i in items],
                'automaticPricing':any('pricingRevision' in i for i in items),
                "printifyShipping": pod_shipping, "officeShipping": office_shipping, "currency": "USD", "expiresAt": now + 900}

    def prepare(self, body):
        cart = cart_input(body.get("items"))
        self.holds.check(json.loads(cart))
        try:
            reference = str(UUID(body.get("requestId", ""), version=4))
            if reference != body.get("requestId"):
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(400, "Invalid checkout request reference.") from None
        with self.connect() as db:
            existing = db.execute("SELECT * FROM orders WHERE request_id=?", (reference,)).fetchone()
            quote = db.execute("SELECT * FROM quotes WHERE id=?", (str(body.get("quoteId", "")),)).fetchone()
        if existing:
            if existing["cart"] != cart or existing["quote_id"] != body.get("quoteId") or existing["cancelled"]:
                raise HTTPException(409, "Start a new checkout for the changed cart or address.")
            if existing["created"] < time.time() - 3600:
                raise HTTPException(409, "This checkout has expired. Get a fresh quote.")
            return dict(existing)
        if not quote or quote["cart"] != cart or quote["created"] < time.time() - 900:
            raise HTTPException(409, "Refresh your shipping quote before checkout.")
        address = json.loads(quote["address"])
        current, _ = self.price(cart, live=bool(address), country=address["country"] if address else None)
        items = json.loads(quote["items"])
        for item,quoted in zip(current,items):
            if item.get('pricingRevision') and item.get('pricingRevision')==quoted.get('pricingRevision'):
                item['cents']=quoted['cents']
        if json.dumps(current, sort_keys=True) != json.dumps([{k:v for k,v in i.items() if k!='procurement'} for i in items], sort_keys=True):
            raise HTTPException(409, "Prices or options changed. Refresh your quote.")
        for item in items:
            if item['kind'] in {'aliexpress','mouser'} and item not in self.automatic_mouser(items):
                live_quote=self.supplier_quote_factory(item['kind']).quote(item,address)
                if live_quote['totalCents']>item['procurement']['totalCents'] or live_quote['service']!=item['procurement']['service']:
                    raise HTTPException(409,'Price or shipping changed. Refresh your quote.')
        automatic=self.automatic_mouser(items)
        if automatic:self.mouser_quote(automatic,address,automatic[0]['procurement'])
        self.inventory() if any(i["kind"] == "office" for i in items) else None
        session = secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM orders WHERE request_id=?", (reference,)).fetchone()
            if existing:
                if existing["cart"] != cart or existing["quote_id"] != body.get("quoteId") or existing["cancelled"]:
                    raise HTTPException(409, "This checkout reference belongs to another cart or address.")
                return dict(existing)
            for i in items:
                if i["kind"] == "office":
                    stock = db.execute("SELECT stock FROM inventory WHERE product=?", (i["id"],)).fetchone()[0]
                    held = db.execute("SELECT COALESCE(SUM(qty),0) FROM reservations WHERE product=?", (i["id"],)).fetchone()[0]
                    if stock - held < i["qty"]:
                        raise HTTPException(409, "An office item sold out. Update your cart.")
            amount = sum(i["cents"] * i["qty"] for i in items) + quote["shipping"]
            db.execute("INSERT INTO orders(request_id,session,cart,items,amount,created,address,shipping,quote_id) VALUES(?,?,?,?,?,?,?,?,?)",
                       (reference, session, cart, quote["items"], amount, int(time.time()), quote["address"], quote["shipping"], quote["id"]))
            for i in items:
                if i["kind"] == "office":
                    db.execute("INSERT INTO reservations VALUES(?,?,?)", (session, i["id"], i["qty"]))
            return dict(db.execute("SELECT * FROM orders WHERE session=?", (session,)).fetchone())

    def mark_paid(self, order, paid):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if paid:
                if not order["paid"]:
                    db.execute("INSERT OR IGNORE INTO sale_events(session,confirmed) VALUES(?,?)", (order["session"],int(time.time())))
                for row in db.execute("SELECT * FROM reservations WHERE session=?", (order["session"],)).fetchall():
                    db.execute("UPDATE inventory SET stock=stock-? WHERE product=?", (row["qty"], row["product"]))
                db.execute("DELETE FROM reservations WHERE session=?", (order["session"],))
                kinds = {i.get("kind", "digital") for i in json.loads(order["items"])} - {"digital"}
                for kind in kinds:
                    db.execute("INSERT OR IGNORE INTO fulfillments(session,kind,state,updated) VALUES(?,?,?,?)",
                               (order["session"], kind, "queued" if kind == "printify" or (kind=='mouser' and self.automatic_mouser(json.loads(order['items']))) else "ready-to-order" if kind in {"aliexpress","mouser"} else "awaiting-submission" if kind == "keycaps" else "ready-to-ship", int(time.time())))
                if "keycaps" in kinds and self.packets:
                    self.packets.enqueue(db, order["session"])
            elif order["paid"]:
                db.execute("UPDATE fulfillments SET error='Payment refunded or no longer fully paid. Review in Square and contact supplier before shipping.',updated=? WHERE session=?",
                           (int(time.time()), order["session"]))
            db.execute("UPDATE orders SET paid=? WHERE session=?", (int(paid), order["session"]))

    def fulfillments(self, session):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM fulfillments WHERE session=? ORDER BY kind", (session,)).fetchall()
            order=db.execute('SELECT items FROM orders WHERE session=?',(session,)).fetchone()
        automatic=bool(order and self.automatic_mouser(json.loads(order['items'])))
        return [{"kind": r["kind"], "state": r["state"], "supplierId": r["supplier_id"], "error": r["error"],
                 "shipments": json.loads(r["shipments"]), "updated": r["updated"], 'automatic':r['kind']=='printify' or (r['kind']=='mouser' and automatic)} for r in rows]

    def update(self, session, kind, state, supplier_id=None, error="", shipments=None):
        with self.connect() as db:
            db.execute("UPDATE fulfillments SET state=?,supplier_id=COALESCE(?,supplier_id),error=?,shipments=COALESCE(?,shipments),updated=? WHERE session=? AND kind=?",
                       (state, supplier_id, error, json.dumps(shipments) if shipments is not None else None, int(time.time()), session, kind))

    def process_printify(self, order):
        fulfillment = next((f for f in self.fulfillments(order["session"]) if f["kind"] == "printify"), None)
        if not fulfillment or fulfillment["state"] in {"delivered", "canceled"}:
            return
        supplier = self.printify()
        if not supplier:
            raise PrintifyUnavailable("Printify connection needs attention.")
        if any(i.get("kind") == "printify" and i.get("shop_id") != supplier.shop_id for i in json.loads(order["items"])):
            raise PrintifyUnavailable("Printify store changed after payment. Restore the original connection before fulfillment.")
        external = "RODDY-" + order["request_id"]
        supplier_id = fulfillment["supplierId"]
        if not supplier_id:
            # Both crash recovery and unknown POST outcomes stop here until an
            # existing order can be located. Only a fresh queued job can POST.
            if fulfillment["state"] != "queued":
                found = supplier.find_order(external)
                if not found:
                    self.update(order["session"], "printify", "review", error="Submission outcome unknown. Search Printify for " + external + ". Reconcile this order before retrying; never create a duplicate.")
                    return
                supplier_id = found["id"]
            else:
                if not self.check_printify_cost(order,supplier):return
                self.update(order["session"], "printify", "submitting")
                result = supplier.submit_order(external, self.supplier_lines(json.loads(order["items"])), json.loads(order["address"]))
                supplier_id = result["id"]
            self.update(order["session"], "printify", "submitted", supplier_id)
        current = supplier.order(supplier_id)
        status = current.get("status", "pending")
        lines = current.get("line_items", [])
        actual_total=self.printify_total(order,current)
        if actual_total is not None:self.records.supplier_total(order,'Printify',supplier_id,actual_total)
        # Avoid a production call while Printify is still calculating/creating
        # the order. Once ready, trigger it explicitly, unless already started.
        if status == "on-hold" and not current.get("sent_to_production_at") and not any(i.get("sent_to_production_at") for i in lines):
            if not self.check_printify_cost(order,supplier,current):return
            if not self.check_payment(order):
                self.mark_paid(order,False);return
            supplier.send_to_production(supplier_id)
            status = "sending-to-production"
        issue = "Check Printify: " + status if status in {"payment-not-received", "has-issues", "unfulfillable", "source-check-failed"} else ""
        if actual_total is not None:
            items=[i for i in json.loads(order['items']) if i.get('kind')=='printify']
            retail=sum(i['cents']*i['qty'] for i in items)
            charged=items[0].get('procurement',{}).get('shippingCents',order['shipping'] if all(i.get('kind') in {'printify','digital'} for i in json.loads(order['items'])) else 0)
            if actual_total>retail+charged-round((retail+charged)*.04)-30:
                issue='Printify reported a cost above the paid-order allowance. Review the supplier invoice and pricing; new purchases are suspended.'
                self.holds.suspend(items,issue)
        shipments = [{"carrier": str(s.get("carrier", ""))[:100], "number": str(s.get("number", ""))[:150],
                      "url": s.get("url", "") if re.match(r"^https?://", str(s.get("url", ""))) else "",
                      "deliveredAt": s.get("delivered_at")} for s in current.get("shipments", [])]
        self.update(order["session"], "printify", "delivered" if shipments and all(s["deliveredAt"] for s in shipments) else status,
                    supplier_id, issue, shipments)

    @staticmethod
    def printify_total(order,current):
        from collections import Counter
        items=[i for i in json.loads(order['items']) if i.get('kind')=='printify']
        expected=Counter()
        for i in items:expected[(i['product_id'],i['variant_id'])]+=i['qty']
        actual=Counter();costs=[]
        for line in current.get('line_items',[]):
            qty=line.get('quantity');cost=line.get('cost')
            if type(qty) is not int or qty<1 or type(cost) is not int or cost<0:return None
            actual[(line.get('product_id'),line.get('variant_id'))]+=qty;costs.append(cost*qty)
        shipping=current.get('total_shipping');tax=current.get('total_tax')
        if actual!=expected or type(shipping) is not int or shipping<0 or type(tax) is not int or tax<0:return None
        return sum(costs)+shipping+tax

    def check_printify_cost(self,order,supplier,current=None):
        items=[i for i in json.loads(order['items']) if i.get('kind')=='printify']
        try:self.holds.check(items)
        except HTTPException:
            self.update(order['session'],'printify','review',error='Purchasing suspended pending product pricing review.');return False
        retail=sum(i['cents']*i['qty'] for i in items)
        charged=items[0].get('procurement',{}).get('shippingCents')
        if charged is None:
            charged=order['shipping'] if all(i.get('kind') in {'printify','digital'} for i in json.loads(order['items'])) else 0
        goods=0;bad=[]
        for item in items:
            if current is None:
                variant=next((v for v in supplier.product(item['product_id'])['variants'] if v['id']==item['variant_id']),{})
                cost=variant.get('costCents')
            else:
                line=next((v for v in current.get('line_items',[]) if v.get('product_id')==item['product_id'] and v.get('variant_id')==item['variant_id']),{})
                if line.get('quantity')!=item['qty']:raise PrintifyUnavailable('Printify quantities changed. Review before production.')
                cost=line.get('cost')
            if type(cost) is not int or cost<0:raise PrintifyUnavailable('Printify costs are not available. Production is held for review.')
            goods+=cost*item['qty']
            if cost>=item['cents']:bad.append(item)
        shipping=supplier.quote_shipping(self.supplier_lines(items),json.loads(order['address'])) if current is None else current.get('total_shipping')
        tax=0 if current is None else current.get('total_tax')
        if type(shipping) is not int or shipping<0 or type(tax) is not int or tax<0:raise PrintifyUnavailable('Printify shipping or tax is unavailable. Production is held for review.')
        if bad or goods+shipping+tax>retail+charged-round((retail+charged)*.04)-30:
            reason='Printify fulfillment cost exceeds the retail allowance after shipping, tax and a 4% + $0.30 fee reserve. Review pricing and this paid order.'
            self.holds.suspend(bad or items,reason)
            self.update(order['session'],'printify','review',error=reason);return False
        return True

    def was_paid(self, session):
        with self.connect() as db:return bool(db.execute('SELECT 1 FROM sale_events WHERE session=?',(session,)).fetchone())

    def tick(self):
        if not self.lock.acquire(blocking=False):
            return
        try:
            with self.connect() as db:
                rows = db.execute("SELECT * FROM orders WHERE cancelled=0 AND (created>? OR EXISTS(SELECT 1 FROM sale_events e WHERE e.session=orders.session)) AND checked<? ORDER BY checked LIMIT 50", (int(time.time()) - 30 * 86400, int(time.time()) - 30)).fetchall()
            for row in rows:
                order = dict(row)
                try:
                    with self.connect() as db:
                        db.execute("UPDATE orders SET checked=? WHERE session=?", (int(time.time()) + (86370 if order["created"] < time.time()-30*86400 else 270 if order["paid"] else 0), order["session"]))
                    if not order["provider_id"]:
                        # Recover a Square timeout with the original idempotency
                        # key, including when the buyer never returns to the site.
                        self.recover(order)
                        with self.connect() as db:
                            order = dict(db.execute("SELECT * FROM orders WHERE session=?", (order["session"],)).fetchone())
                    paid = self.check_payment(order)
                    self.mark_paid(order, paid)
                    if paid and self.enabled and self.provider.mode == "live":
                        if self.packets:
                            self.packets.process(order)
                        try:
                            self.process_printify(order)
                        except PrintifyUnavailable as exc:
                            f=next((f for f in self.fulfillments(order['session']) if f['kind']=='printify'),None)
                            if f:self.update(order['session'],'printify','review' if f['state']=='submitting' else f['state'],error=str(exc))
                        if self.mouser_factory:
                            from .mouser_fulfillment import process
                            process(self,order)
                    elif not paid and not order["paid"] and not self.was_paid(order["session"]) and order["created"] < time.time() - 3600 and order["link_id"]:
                        # Delete the hosted link BEFORE releasing reservations.
                        self.provider.cancel_checkout(order["link_id"])
                        if self.check_payment(order):
                            self.mark_paid(order, True)
                        else:
                            with self.connect() as db:
                                db.execute("UPDATE orders SET cancelled=1 WHERE session=?", (order["session"],))
                                db.execute("DELETE FROM reservations WHERE session=?", (order["session"],))
                except (PaymentUnavailable, PrintifyUnavailable) as exc:
                    f = next((f for f in self.fulfillments(order["session"]) if f["kind"] == "printify"), None)
                    if f:
                        self.update(order["session"], "printify", "review" if f["state"] == "submitting" else f["state"], error=str(exc))
        finally:
            self.lock.release()
