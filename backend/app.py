"""Checkout, digital delivery and fulfillment service for the droplet."""

import hashlib
from contextlib import contextmanager, asynccontextmanager
import threading
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .square import Square, PaymentUnavailable, PaymentInputError
from .printify import load_connection, PrintifyUnavailable
from .commerce import Commerce
from .forum import register_forum


def checkout_url(value):
    url = urlsplit(value)
    return (url.scheme == "https" and not url.username and not url.password
            and url.hostname in {"square.link", "checkout.square.site", "sandbox.square.link"})


def create_app(*, database=None, private_dir=None, manifest=None, provider=None,
               catalog_loader=None, enabled=None, site=None, public_url=None, printify_config=None, physical_enabled=None, printify_factory=None, worker_enabled=None):
    database = Path(database or os.getenv("STORE_DATABASE", "/var/lib/roddy-store/orders.sqlite3"))
    private_dir = Path(private_dir or os.getenv("STORE_PRIVATE_DIR", "/var/lib/roddy-store/files")).resolve()
    manifest = manifest or os.getenv("STORE_MANIFEST", "/etc/roddy-store/digital-products.json")
    site = (site or os.getenv("SITE_URL", "https://roddy.world")).rstrip("/")
    public_url = (public_url or os.getenv("STORE_PUBLIC_URL", "")).rstrip("/")
    enabled = enabled if enabled is not None else os.getenv("STORE_CHECKOUT_ENABLED", "false") == "true"
    provider = provider or Square(os.getenv("SQUARE_ACCESS_TOKEN", ""),
                                  os.getenv("SQUARE_LOCATION_ID", ""),
                                  os.getenv("SQUARE_MODE", "sandbox"))
    admin_login = os.getenv("ADMIN_GITHUB_LOGIN", "lionsarmor")
    printify_config = printify_config or os.getenv("PRINTIFY_CONFIG", "/etc/roddy-store/printify.json")
    physical_enabled = physical_enabled if physical_enabled is not None else os.getenv("STORE_PHYSICAL_ENABLED", "false") == "true"
    worker_enabled = worker_enabled if worker_enabled is not None else os.getenv("STORE_FULFILLMENT_WORKER", "false") == "true"
    printify_factory = printify_factory or (lambda: load_connection(printify_config))
    origins = os.getenv("ALLOWED_ORIGINS", "https://roddy.world,https://www.roddy.world").split(",")

    def load_catalog():
        url = os.getenv("PRODUCTS_URL", "https://raw.githubusercontent.com/lionsarmor/RODDY-STORE-FRONT/main/public/data/products.json")
        if not url.startswith("https://"):
            raise ValueError("PRODUCTS_URL must use HTTPS")
        try:
            response = httpx.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(503, "Catalog is unavailable. Please try again.") from exc

    catalog_loader = catalog_loader or load_catalog
    database.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect():
        db = sqlite3.connect(database, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    with connect() as db:
        db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS orders (
          request_id TEXT PRIMARY KEY, session TEXT NOT NULL UNIQUE,
          cart TEXT NOT NULL, items TEXT NOT NULL, amount INTEGER NOT NULL,
          created INTEGER NOT NULL, provider_id TEXT, url TEXT, paid INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tickets (
          digest TEXT PRIMARY KEY, session TEXT NOT NULL REFERENCES orders(session),
          product TEXT NOT NULL, expires INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS limits (
          bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, expires INTEGER NOT NULL
        );
        """)
    os.chmod(database, 0o600)

    @asynccontextmanager
    async def lifespan(app):
        stop = threading.Event()
        def work():
            while not stop.is_set():
                try:
                    commerce.tick()
                except Exception:
                    # No exception payloads: providers may include personal data.
                    import logging
                    logging.getLogger("roddy-store").error("Fulfillment worker needs attention; check store admin.")
                stop.wait(30)
        thread = threading.Thread(target=work, daemon=True) if worker_enabled else None
        if thread:
            thread.start()
        yield
        stop.set()
        if thread:
            thread.join(timeout=5)

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=origins,
                       allow_methods=["POST", "GET"], allow_headers=["content-type", "authorization"])

    @app.middleware("http")
    async def headers(request, call_next):
        # No API endpoint accepts a body larger than a small cart. Reject before parsing.
        if request.method == "POST":
            body = await request.body()
            if len(body) > 8192:
                return JSONResponse({"error": "Request too large."}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(HTTPException)
    async def http_error(_, exc):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_, exc):
        return JSONResponse({"error": "Invalid request."}, status_code=422)

    @app.exception_handler(PaymentInputError)
    async def payment_input_error(_, exc):
        return JSONResponse({"error": str(exc)}, status_code=400)

    @app.exception_handler(PaymentUnavailable)
    async def provider_error(_, exc):
        return JSONResponse({"error": str(exc)}, status_code=503)

    @app.exception_handler(PrintifyUnavailable)
    async def printify_error(_, exc):
        return JSONResponse({"error": str(exc)}, status_code=503)

    def rate_limit(request, kind, maximum):
        # systemd runs one uvicorn process; SQLite makes limits durable across restarts.
        # Caddy strips spoofed forwarded headers; uvicorn trusts only loopback proxies.
        address = request.client.host if request.client else "unknown"
        now = int(time.time())
        bucket = hashlib.sha256(f"{kind}:{address}:{now // 60}".encode()).hexdigest()
        with connect() as db:
            db.execute("DELETE FROM limits WHERE expires < ?", (now,))
            db.execute("INSERT INTO limits VALUES (?, 1, ?) ON CONFLICT(bucket) DO UPDATE SET count=count+1",
                       (bucket, now + 120))
            count = db.execute("SELECT count FROM limits WHERE bucket=?", (bucket,)).fetchone()[0]
        if count > maximum:
            raise HTTPException(429, "Too many requests. Please try again in a minute.")

    def assets():
        try:
            data = manifest if isinstance(manifest, dict) else json.loads(Path(manifest).read_text())
            if not isinstance(data, dict):
                raise ValueError()
            return data
        except (OSError, ValueError) as exc:
            raise HTTPException(503, "Digital delivery is not configured yet.") from exc

    def private_file(item):
        if provider.mode == "sandbox" and not item.get("sandbox"):
            raise HTTPException(503, "Sandbox checkout requires a test-only download file.")
        filename = item.get("file", "")
        checksum = item.get("sha256", "")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.zip", filename):
            raise HTTPException(503, "Invalid digital delivery configuration.")
        path = (private_dir / filename).resolve()
        if (path.parent != private_dir or not path.is_file()
                or not re.fullmatch(r"[a-f0-9]{64}", checksum)
                or hashlib.sha256(path.read_bytes()).hexdigest() != checksum):
            raise HTTPException(503, "The download is temporarily unavailable. Please contact RODDY.")
        return path

    def normalize_cart(body):
        raw = body.get("items") if isinstance(body, dict) else None
        if not isinstance(raw, list) or not 1 <= len(raw) <= 10:
            raise HTTPException(400, "Choose at least one paid digital product.")
        ids = []
        for item in raw:
            if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
                    or type(item.get("qty")) is not int or item["qty"] != 1
                    or item["id"] in ids):
                raise HTTPException(400, "Digital downloads allow one copy of each product per order.")
            ids.append(item["id"])
        return json.dumps(sorted(ids))

    def price_cart(cart):
        products = {p["id"]: p for p in catalog_loader()["products"]}
        files = assets()
        items = []
        for product_id in json.loads(cart):
            p = products.get(product_id)
            if (not p or not p.get("active") or p.get("status") != "available"
                    or p.get("pricePending") or p.get("type") != "digital"
                    or p.get("downloadUrl") or "free" in p.get("tags", [])
                    or p.get("trackStock", True) or product_id not in files):
                raise HTTPException(409, "An item is unavailable for paid digital checkout.")
            price = p.get("price")
            if type(price) not in (float, int) or not 0 < price <= 999999:
                raise HTTPException(409, "Invalid product price.")
            cents = round(price * 100)
            if cents < 1 or abs(price * 100 - cents) > 0.00001:
                raise HTTPException(409, "Invalid product price.")
            item = {"id": product_id, "name": p["name"], "cents": cents, **files[product_id]}
            # The manifest only specifies server-owned filenames and hashes.
            item.update(id=product_id, name=p["name"], cents=cents)
            private_file(item)
            items.append(item)
        return items

    def get_order(session):
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", session):
            raise HTTPException(404, "Order not found.")
        with connect() as db:
            row = db.execute("SELECT * FROM orders WHERE session=?", (session,)).fetchone()
        if not row:
            raise HTTPException(404, "Order not found.")
        if row["created"] < time.time() - 30 * 86400:
            raise HTTPException(410, "This order link has expired. Contact RODDY with your payment receipt.")
        return dict(row)

    def verify(order):
        paid = bool(order["provider_id"] and provider.paid(order["provider_id"], order["amount"]))
        commerce.mark_paid(order, paid)
        return paid

    commerce = Commerce(connect, catalog_loader, price_cart, provider, printify_factory, physical_enabled)
    app.state.commerce = commerce

    @app.post("/quote")
    def quote(request: Request, body: dict):
        rate_limit(request, "quote", 10)
        if not enabled or not provider.configured:
            raise HTTPException(503, "Checkout is unavailable.")
        if request.headers.get("origin") not in origins:
            raise HTTPException(403, "Start checkout from the RODDY store.")
        return commerce.quote(body)

    @app.get("/inventory")
    def inventory(request: Request):
        rate_limit(request, "inventory", 30)
        return {"items": [{"id": i["id"], "available": i["available"]} for i in commerce.inventory()]}

    @app.get("/health")
    def health(request: Request):
        rate_limit(request, "health", 10)
        configured = provider.configured
        account_ready = provider.check_account() if configured else False
        return {"provider": provider.name, "configured": configured,
                "accountReady": account_ready, "mode": provider.mode,
                "checkoutEnabled": enabled, "physicalEnabled": physical_enabled, "fulfillmentWorker": worker_enabled}

    @app.post("/checkout")
    def checkout(request: Request, body: dict):
        rate_limit(request, "checkout", 10)
        if not enabled or not provider.configured or not public_url.startswith("https://"):
            raise HTTPException(503, "Online checkout is getting ready. Please check back soon.")
        if request.headers.get("origin") not in origins:
            raise HTTPException(403, "Checkout must start from the RODDY store.")
        if body.get("quoteId"):
            order = commerce.prepare(body)
            return finish_checkout(order)
        cart = normalize_cart(body)
        try:
            request_id = str(UUID(body.get("requestId", ""), version=4))
            if request_id != body.get("requestId"):
                raise ValueError()
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(400, "Invalid checkout request reference.") from exc
        with connect() as db:
            existing = db.execute("SELECT * FROM orders WHERE request_id=?", (request_id,)).fetchone()
        if not existing:
            items = price_cart(cart)
            with connect() as db:
                db.execute("INSERT OR IGNORE INTO orders(request_id,session,cart,items,amount,created) VALUES(?,?,?,?,?,?)",
                           (request_id, secrets.token_urlsafe(32), cart, json.dumps(items),
                            sum(item["cents"] for item in items), int(time.time())))
                existing = db.execute("SELECT * FROM orders WHERE request_id=?", (request_id,)).fetchone()
        order = dict(existing)
        if order["cart"] != cart:
            raise HTTPException(409, "This checkout reference belongs to a different cart.")
        if order["created"] < time.time() - 3600:
            raise HTTPException(409, "This checkout has expired. Start a new checkout from your cart.")
        return finish_checkout(order)

    def finish_checkout(order):
        if order.get("cancelled"):
            raise HTTPException(409, "This checkout was canceled. Start again from your cart.")
        if not order["url"]:
            order["items"] = json.loads(order["items"]) if isinstance(order["items"], str) else order["items"]
            if order.get("address") and isinstance(order["address"], str):
                order["address"] = json.loads(order["address"])
            result = provider.create_checkout(order, site + "/order.html#session_id=" + order["session"])
            provider_id, url = result[:2]
            link_id = result[2] if len(result) > 2 else None
            if not checkout_url(url):
                raise HTTPException(503, "Payment service returned an invalid destination.")
            with connect() as db:
                db.execute("UPDATE orders SET provider_id=?,url=?,link_id=? WHERE request_id=?", (provider_id, url, link_id, order["request_id"]))
            order["url"] = url
        return {"url": order["url"], "provider": provider.name, "sessionId": order["session"]}

    commerce.recover = finish_checkout

    @app.post("/order")
    def order_status(request: Request, body: dict):
        rate_limit(request, "order", 30)
        order = get_order(str(body.get("sessionId", "")))
        paid = verify(order)
        downloads = []
        now = int(time.time())
        if paid:
            with connect() as db:
                db.execute("DELETE FROM tickets WHERE expires < ?", (now,))
                for item in json.loads(order["items"]):
                    if item.get("kind", "digital") != "digital":
                        continue
                    private_file(item)
                    ticket = secrets.token_urlsafe(32)
                    db.execute("INSERT INTO tickets VALUES(?,?,?,?)",
                               (hashlib.sha256(ticket.encode()).hexdigest(), order["session"], item["id"], now + 900))
                    downloads.append({"name": item["name"], "filename": item["file"],
                                      "url": public_url + "/download/" + ticket,
                                      "expiresAt": now + 900})
        return {"paid": paid, "amountTotal": order["amount"], "currency": "USD", "downloads": downloads,
                "mode": provider.mode, "shipping": order.get("shipping", 0),
                "items": [{"id": i["id"], "variantId": i.get("variantId", ""), "name": i["name"], "qty": i.get("qty", 1), "kind": i.get("kind", "digital"), "label": i.get("label", "")} for i in json.loads(order["items"])],
                "fulfillments": [{k: v for k, v in f.items() if k not in {"supplierId", "error"}} for f in commerce.fulfillments(order["session"])] if paid else []}

    @app.get("/download/{ticket}")
    def download(request: Request, ticket: str):
        rate_limit(request, "download", 20)
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", ticket):
            raise HTTPException(404, "Download not found.")
        with connect() as db:
            row = db.execute("SELECT * FROM tickets WHERE digest=? AND expires>?",
                             (hashlib.sha256(ticket.encode()).hexdigest(), int(time.time()))).fetchone()
        if not row:
            raise HTTPException(410, "Download link expired. Check your order again for a fresh link.")
        order = get_order(row["session"])
        # Re-query Square to revoke new downloads after a refund. Never trust a cached 'paid' flag.
        if not verify(order):
            raise HTTPException(403, "Payment is not confirmed for this download.")
        item = next(i for i in json.loads(order["items"]) if i["id"] == row["product"])
        return FileResponse(private_file(item), media_type="application/zip", filename=item["file"])

    def require_admin(request):
        rate_limit(request, "admin", 60)
        token = request.headers.get("authorization", "")
        if not token.startswith("Bearer "):
            raise HTTPException(401, "Sign in with GitHub first.")
        try:
            response = httpx.get("https://api.github.com/user", headers={"Authorization": token}, timeout=15)
            response.raise_for_status()
            if response.json().get("login", "").lower() != admin_login.lower():
                raise HTTPException(403, "This GitHub account cannot access store administration.")
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(401, "Could not verify GitHub sign-in.") from exc

    @app.get("/admin/printify")
    def printify_inventory(request: Request, page: int = 1):
        require_admin(request)
        if not 1 <= page <= 10000:
            raise HTTPException(400, "Invalid product page.")
        client = load_connection(printify_config)
        if client is None:
            return {"configured": False, "fulfillmentEnabled": False, "products": [], "hasMore": False}
        shop = next((s for s in client.shops() if s["id"] == client.shop_id), None)
        if not shop:
            raise PrintifyUnavailable("The configured Printify store is no longer accessible. Run setup again.")
        return {"configured": True, "fulfillmentEnabled": physical_enabled and worker_enabled, "shop": shop, **client.products(page)}

    @app.get("/admin/printify/products/{product_id}")
    def printify_product(product_id: str, request: Request):
        require_admin(request)
        client = load_connection(printify_config)
        if client is None:
            raise HTTPException(409, "Connect Printify using the droplet setup command first.")
        return {"shopId": client.shop_id, "product": client.product(product_id)}

    @app.get("/admin/orders")
    def admin_orders(request: Request):
        require_admin(request)
        with connect() as db:
            rows = db.execute("SELECT * FROM orders ORDER BY created DESC LIMIT 100").fetchall()
        return {"data": [{"id": row["request_id"], "providerId": row["provider_id"], "created": row["created"],
                          "amount_total": row["amount"], "shipping": row["shipping"], "currency": "USD",
                          "payment_status": "paid" if row["paid"] else "canceled" if row["cancelled"] else "unconfirmed",
                          "address": json.loads(row["address"]) if row["address"] else None,
                          "items": [{"id": i["id"], "name": i["name"], "qty": i.get("qty", 1), "kind": i.get("kind", "digital"), "label": i.get("label", "")} for i in json.loads(row["items"])],
                          "fulfillments": commerce.fulfillments(row["session"])} for row in rows], "has_more": False}

    @app.get("/admin/inventory")
    def admin_inventory(request: Request):
        require_admin(request)
        return {"items": commerce.inventory()}

    @app.post("/admin/inventory/{product_id}")
    def set_inventory(product_id: str, request: Request, body: dict):
        require_admin(request)
        stock = body.get("stock")
        if type(stock) is not int or not 0 <= stock <= 100000:
            raise HTTPException(400, "Stock must be a whole number from zero to 100000.")
        if product_id not in {i["id"] for i in commerce.inventory()}:
            raise HTTPException(404, "Office product not found.")
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            held = db.execute("SELECT COALESCE(SUM(qty),0) FROM reservations WHERE product=?", (product_id,)).fetchone()[0]
            if stock < held:
                raise HTTPException(409, "Stock cannot be lower than current reservations. Cancel unpaid orders first.")
            db.execute("UPDATE inventory SET stock=? WHERE product=?", (stock, product_id))
        return {"items": commerce.inventory()}

    @app.post("/admin/orders/{reference}/shipment")
    def office_shipment(reference: str, request: Request, body: dict):
        require_admin(request)
        with connect() as db:
            row = db.execute("SELECT * FROM orders WHERE request_id=?", (reference,)).fetchone()
        if not row:
            raise HTTPException(404, "Order not found.")
        order = dict(row)
        if not verify(order):
            raise HTTPException(409, "Payment must be fully confirmed before shipping.")
        if not any(i.get("kind") == "office" for i in json.loads(order["items"])):
            raise HTTPException(409, "This order has no office shipment.")
        carrier, number, url = (str(body.get(k, "")).strip() for k in ["carrier", "number", "url"])
        if not carrier or not number or len(carrier) > 100 or len(number) > 150 or (url and (len(url) > 1000 or not urlsplit(url).scheme in {"http", "https"} or not urlsplit(url).hostname or urlsplit(url).username)):
            raise HTTPException(400, "Enter a carrier, tracking number and optional HTTP(S) tracking URL.")
        commerce.update(order["session"], "office", "shipped", shipments=[{"carrier": carrier, "number": number, "url": url}])
        return {"saved": True}

    @app.post("/admin/orders/{reference}/cancel")
    def cancel_unpaid_order(reference: str, request: Request, body: dict):
        require_admin(request)
        with connect() as db:
            row = db.execute("SELECT * FROM orders WHERE request_id=?", (reference,)).fetchone()
        if not row:
            raise HTTPException(404, "Order not found.")
        order = dict(row)
        if order["cancelled"]:
            return {"saved": True}
        if order["provider_id"] and verify(order):
            raise HTTPException(409, "Paid orders need a refund in Square and supplier review before cancellation.")
        if not order["provider_id"]:
            finish_checkout(order)
            with connect() as db:
                order = dict(db.execute("SELECT * FROM orders WHERE request_id=?", (reference,)).fetchone())
        if not order["link_id"]:
            raise HTTPException(409, "This older payment link must be canceled in Square.")
        provider.cancel_checkout(order["link_id"])
        if verify(order):
            raise HTTPException(409, "Payment arrived during cancellation. Review this paid order before refunding or shipping.")
        with connect() as db:
            db.execute("UPDATE orders SET cancelled=1 WHERE session=?", (order["session"],))
            db.execute("DELETE FROM reservations WHERE session=?", (order["session"],))
        return {"saved": True}

    @app.post("/admin/orders/{reference}/reconcile")
    def reconcile_order(reference: str, request: Request, body: dict):
        require_admin(request)
        with connect() as db:
            row = db.execute("SELECT * FROM orders WHERE request_id=?", (reference,)).fetchone()
        if not row:
            raise HTTPException(404, "Order not found.")
        order = dict(row)
        if not verify(order):
            raise HTTPException(409, "Payment is not confirmed.")
        supplier = printify_factory()
        if not supplier:
            raise HTTPException(409, "Connect Printify first.")
        found = supplier.find_order("RODDY-" + reference)
        if not found:
            raise HTTPException(409, "No matching Printify order found. Check the supplier dashboard before creating anything manually.")
        commerce.update(order["session"], "printify", "submitted", supplier_id=found["id"])
        return {"saved": True}

    register_forum(app, connect, require_admin, rate_limit, origins)
    return app
