import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from backend.app import create_app
from backend.printify import Printify, PrintifyUnavailable
from backend.square import Square
from backend.test_checkout import FakeProvider

ADDRESS = dict(first_name='Test', last_name='Buyer', email='buyer@example.com', phone='2025550100',
               country='US', region='DC', address1='1600 Pennsylvania Ave NW', address2='', city='Washington', zip='20500')

class Supplier:
    shop_id = 123
    available = True
    submission_timeout = False
    status = 'on-hold'
    cost = 1200
    tax = 0
    def __init__(self):
        self.submitted = []
        self.production = []
        self.found = None
        self.shipments = []
    def product(self, pid):
        return {'variants': [{'id': 10, 'enabled': True, 'available': self.available, 'costCents': self.cost}]}
    def quote_shipping(self, lines, address):
        return 1234
    def submit_order(self, external, lines, address):
        self.submitted.append((external, copy.deepcopy(lines), copy.deepcopy(address)))
        if self.submission_timeout:
            raise PrintifyUnavailable('Unknown submission outcome')
        return {'id': 'supplier123'}
    def find_order(self, external):
        return self.found
    def order(self, sid):
        return {'id': sid, 'status': self.status,
                'line_items': [{**line,'cost':self.cost} for line in self.submitted[0][1]] if self.submitted else [],
                'total_shipping':1234,'total_tax':self.tax,'shipments': copy.deepcopy(self.shipments)}
    def send_to_production(self, sid):
        self.production.append(sid)
        self.status = 'in-production'

class MixedCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.database = self.root/'orders.sqlite3'
        release = self.root/'desk.zip'; release.write_bytes(b'private paid game')
        manifest = {'desk': {'file': release.name, 'sha256': hashlib.sha256(release.read_bytes()).hexdigest()}}
        base = {'active': True, 'status': 'available', 'trackStock': False, 'price': 17.99}
        self.catalog = {'products': [
            {**base, 'id': 'desk', 'name': 'Desk', 'type': 'digital', 'price': 3.99},
            {**base, 'id': 'hoodie', 'name': 'Hoodie', 'type': 'physical', 'merch': {'provider': 'printify', 'shopId': 123,
                'productId': 'hoodie123', 'shippingCountries': ['US','CA'], 'variants': [
                    {'id': '10', 'providerVariantId': 10, 'enabled': True, 'available': True, 'price': 35.99, 'size': 'S', 'color': 'Black'}]}},
            {**base, 'id': 'office', 'name': 'Office gadget', 'type': 'physical', 'trackStock': True, 'stock': 2,
             'officeShipping': {'US': {'firstItem': 6, 'additionalItem': 2}}}
        ]}
        self.provider = FakeProvider(); self.provider.mode = 'live'
        self.supplier = Supplier()
        self.app = create_app(database=self.database, private_dir=self.root, manifest=manifest, provider=self.provider,
                              catalog_loader=lambda: self.catalog, enabled=True, physical_enabled=True,
                              printify_factory=lambda: self.supplier, site='https://roddy.world', public_url='https://api.example.test')
        self.client = TestClient(self.app)
        self.items = [{'id': 'desk', 'qty': 1}, {'id':'hoodie','variantId':'10','qty':2}, {'id':'office','qty':1}]
        self.origin = {'origin':'https://roddy.world'}
    def quote(self, items=None, address=None):
        return self.client.post('/quote',json={'items':self.items if items is None else items,'address':address or ADDRESS},headers=self.origin)
    def checkout(self, quote, items=None, ref=None):
        return self.client.post('/checkout',json={'quoteId':quote['quoteId'],'items':items or self.items,'requestId':ref or str(uuid4())},headers=self.origin)
    def order(self, session):
        with sqlite3.connect(self.database) as db:
            db.row_factory=sqlite3.Row
            return dict(db.execute('SELECT * FROM orders WHERE session=?',(session,)).fetchone())
    def tick(self):
        with sqlite3.connect(self.database) as db: db.execute('UPDATE orders SET checked=0')
        self.app.state.commerce.tick()
    def admin(self, method, path, body=None):
        response=type('Response',(),{'raise_for_status':lambda _:None,'json':lambda _:{'login':'lionsarmor'}})()
        with patch('backend.app.httpx.get',return_value=response):
            return self.client.request(method,path,json=body,headers={'authorization':'Bearer owner'})
    def test_pending_supplier_product_cannot_accidentally_become_office_fulfillment(self):
        office = self.catalog['products'][2]
        office['supplier'] = {'provider': 'mouser', 'supplierSku': '123-FPGA', 'fulfillment': 'pending'}
        self.assertEqual(self.quote([{'id': 'office', 'qty': 1}]).status_code, 409)
        self.assertEqual(self.provider.created, [])
        office['supplier']['fulfillment'] = 'office'
        result = self.quote([{'id': 'office', 'qty': 1}])
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['subtotal'], 1799)

    def test_printify_cost_overrun_suspends_new_purchases_and_holds_paid_order(self):
        q=self.quote().json();result=self.checkout(q).json();self.provider.is_paid=True
        self.supplier.cost=9999;self.tick()
        self.assertEqual(self.supplier.submitted,[]);self.assertEqual(self.supplier.production,[])
        self.assertEqual(self.app.state.commerce.fulfillments(result['sessionId'])[1]['state'],'review')
        self.assertIn('hoodie',self.client.get('/inventory').json()['suspendedProducts'])
        self.assertEqual(self.quote().status_code,409)
        self.assertEqual(self.admin('GET','/admin/orders?view=inbox').json()['total'],1)

    def test_printify_tax_overrun_stops_production_without_resubmission(self):
        q=self.quote().json();result=self.checkout(q).json();self.provider.is_paid=True
        self.supplier.tax=100000;self.tick()
        self.assertEqual(len(self.supplier.submitted),1);self.assertEqual(self.supplier.production,[])
        self.assertIn('hoodie',self.client.get('/inventory').json()['suspendedProducts'])
        self.tick();self.assertEqual(len(self.supplier.submitted),1)
        self.assertEqual(self.supplier.production,[])

    def test_printify_tracking_moves_fulfilled_order_to_shipped_then_delivered(self):
        items=[{'id':'hoodie','variantId':'10','qty':1}]
        result=self.checkout(self.quote(items).json(),items).json()
        self.provider.is_paid=True;self.tick()
        self.supplier.status='fulfilled'
        self.supplier.shipments=[{'carrier':'usps','number':'tracking123',
                                 'url':'https://example.com/tracking123','delivered_at':None}]
        self.tick()
        shipped=self.admin('GET','/admin/orders?view=shipped').json()
        self.assertEqual(shipped['total'],1)
        fulfillment=shipped['data'][0]['fulfillments'][0]
        self.assertEqual(fulfillment['state'],'shipped')
        self.assertEqual(fulfillment['shipments'][0]['number'],'tracking123')
        self.assertEqual(shipped['summary']['shipped'],1)
        self.assertEqual(self.admin('GET','/admin/orders?view=progress').json()['total'],0)
        customer=self.client.post('/order',json={'sessionId':result['sessionId']}).json()
        self.assertEqual(customer['fulfillments'][0]['state'],'shipped')
        self.supplier.shipments[0]['delivered_at']='2026-10-22 12:00:00+00:00'
        self.tick()
        delivered=self.admin('GET','/admin/orders?view=shipped').json()
        self.assertEqual(delivered['data'][0]['fulfillments'][0]['state'],'delivered')
        self.assertEqual(len(self.supplier.submitted),1)
        self.assertEqual(len(self.supplier.production),1)

    def test_printify_partial_delivery_does_not_complete_whole_order(self):
        items=[{'id':'hoodie','variantId':'10','qty':2}]
        result=self.checkout(self.quote(items).json(),items).json()
        self.provider.is_paid=True;self.tick()
        self.supplier.status='partially-fulfilled'
        self.supplier.shipments=[{'carrier':'usps','number':'partial123',
                                 'delivered_at':'2026-10-22 12:00:00+00:00'}]
        self.tick()
        fulfillment=self.app.state.commerce.fulfillments(result['sessionId'])[0]
        self.assertEqual(fulfillment['state'],'partially-fulfilled')
        self.assertEqual(fulfillment['shipments'][0]['number'],'partial123')
        self.assertEqual(self.admin('GET','/admin/orders?view=shipped').json()['total'],0)
        self.assertEqual(self.admin('GET','/admin/orders?view=progress').json()['total'],1)

    def test_printify_completed_order_needs_tracking_and_all_packages_delivered(self):
        items=[{'id':'hoodie','variantId':'10','qty':2}]
        result=self.checkout(self.quote(items).json(),items).json()
        self.provider.is_paid=True;self.tick()
        self.supplier.status='fulfilled';self.tick()
        self.assertEqual(self.app.state.commerce.fulfillments(result['sessionId'])[0]['state'],'fulfilled')
        self.supplier.shipments=[{'carrier':'usps','number':'first','delivered_at':'2026-10-22 12:00:00+00:00'},
                                 {'carrier':'usps','number':'second','delivered_at':None}]
        self.tick()
        self.assertEqual(self.app.state.commerce.fulfillments(result['sessionId'])[0]['state'],'shipped')
        self.supplier.shipments[1]['delivered_at']='2026-10-22 13:00:00+00:00'
        self.tick()
        self.assertEqual(self.app.state.commerce.fulfillments(result['sessionId'])[0]['state'],'delivered')

    def test_mixed_order_total_repriced_shipping_and_no_production_before_payment(self):
        q=self.quote(); self.assertEqual(q.status_code,200,q.text); q=q.json()
        self.assertEqual(q['subtotal'],399+3599*2+1799)
        self.assertEqual(q['shipping'],1234+600)
        self.assertEqual(self.supplier.submitted,[])
        ref=str(uuid4()); result=self.checkout(q,ref=ref); self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(self.provider.created[0][0]['amount'],q['amountTotal'])
        self.assertEqual(self.checkout(q,ref=ref).json(),result.json()); self.assertEqual(len(self.provider.created),1)
        self.tick(); self.assertEqual(self.supplier.submitted,[])
        session=result.json()['sessionId']; self.provider.is_paid=True; self.tick()
        self.assertEqual(len(self.supplier.submitted),1)
        external,lines,address=self.supplier.submitted[0]
        self.assertEqual(external,'RODDY-'+ref); self.assertEqual(lines[0]['quantity'],2)
        self.assertEqual(len(lines),1); self.assertEqual(address,ADDRESS)
        self.assertEqual(self.supplier.production,['supplier123'])
        self.tick(); self.assertEqual(len(self.supplier.submitted),1); self.assertEqual(len(self.supplier.production),1)
        status=self.client.post('/order',json={'sessionId':session}).json()
        self.assertTrue(status['paid']); self.assertEqual(len(status['downloads']),1)
        self.assertEqual({f['kind'] for f in status['fulfillments']},{'office','made-to-order'})
        self.assertNotIn('supplierId',json.dumps(status['fulfillments']))
        inventory=self.client.get('/inventory').json()['items'][0]; self.assertEqual(inventory['available'],1)
        self.tick(); self.assertEqual(self.client.get('/inventory').json()['items'][0]['available'],1)
    def test_unknown_supplier_submission_never_blindly_repeated_and_can_reconcile(self):
        result=self.checkout(self.quote().json()).json(); self.provider.is_paid=True; self.supplier.submission_timeout=True
        self.tick(); self.tick(); self.assertEqual(len(self.supplier.submitted),1)
        f=self.app.state.commerce.fulfillments(result['sessionId']); self.assertEqual(next(f for f in f if f['kind']=='printify')['state'],'review')
        self.supplier.found={'id':'supplier123'}; self.tick()
        self.assertEqual(len(self.supplier.submitted),1); self.assertEqual(self.supplier.production,['supplier123'])
    def test_office_reservations_prevent_oversell_and_catalog_cannot_restore_sold_stock(self):
        items=[{'id':'office','qty':2}]; q=self.quote(items).json(); result=self.checkout(q,items).json()
        self.assertEqual(self.quote([{'id':'office','qty':1}]).status_code,409)
        self.provider.is_paid=True; self.tick()
        self.assertEqual(self.client.get('/inventory').json()['items'][0]['available'],0)
        self.catalog['products'][2]['stock']=100
        self.assertEqual(self.client.get('/inventory').json()['items'][0]['available'],0)
        response=self.admin('POST','/admin/inventory/office',{'stock':10}); self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['items'][0]['available'],10)
    def test_quote_is_immutable_expiring_and_not_reusable_for_another_cart(self):
        q=self.quote().json(); self.catalog['products'][1]['merch']['variants'][0]['price']=36.99
        self.assertEqual(self.checkout(q).status_code,409)
        q=self.quote().json()
        with sqlite3.connect(self.database) as db: db.execute('UPDATE quotes SET created=0')
        self.assertEqual(self.checkout(q).status_code,409)
        q=self.quote().json(); self.assertEqual(self.checkout(q,items=[{'id':'desk','qty':1}]).status_code,409)
    def test_supplier_stock_is_checked_at_quote_and_checkout(self):
        q=self.quote().json(); self.supplier.available=False
        self.assertEqual(self.checkout(q).status_code,409)
        self.assertEqual(self.quote().status_code,409)
        self.assertEqual(self.provider.created,[])
    def test_address_missing_rates_and_unsupported_countries_are_rejected(self):
        for address in [{**ADDRESS,'country':'FR'},{**ADDRESS,'zip':'bad'},{**ADDRESS,'email':'bad'},{**ADDRESS,'phone':''}]:
            self.assertEqual(self.quote(address=address).status_code,400)
        ca={**ADDRESS,'country':'CA','region':'ON','zip':'M5V 3L9'}
        self.assertEqual(self.quote(address=ca).status_code,409)
        self.assertEqual(self.quote([{'id':'hoodie','variantId':'10','qty':1}],ca).status_code,200)
    def test_price_tampering_duplicate_variants_and_digital_quantities(self):
        response=self.quote([{**i,'price':.01,'amount':1} for i in self.items]); self.assertEqual(response.json()['subtotal'],9396)
        self.assertEqual(self.quote(self.items+[self.items[1]]).status_code,400)
        self.assertEqual(self.quote([{'id':'desk','qty':2}]).status_code,400)
    def test_office_tracking_requires_owner_paid_order_and_returns_to_customer(self):
        q=self.quote().json(); result=self.checkout(q).json(); session=result['sessionId']; ref=self.order(session)['request_id']
        path='/admin/orders/'+ref+'/shipment'; body={'carrier':'USPS','number':'123','url':'https://tools.usps.com/go/TrackConfirmAction?tLabels=123'}
        self.assertEqual(self.client.post(path,json=body).status_code,401)
        self.assertEqual(self.admin('POST',path,body).status_code,409)
        self.provider.is_paid=True
        self.assertEqual(self.admin('POST',path,{**body,'url':'javascript:alert(1)'}).status_code,400)
        self.assertEqual(self.admin('POST',path,body).status_code,200)
        status=self.client.post('/order',json={'sessionId':session}).json()
        office=next(f for f in status['fulfillments'] if f['kind']=='office'); self.assertEqual(office['state'],'shipped'); self.assertEqual(office['shipments'][0]['number'],'123')
    def test_unpaid_link_is_cancelled_before_stock_is_released(self):
        items=[{'id':'office','qty':2}]; result=self.checkout(self.quote(items).json(),items).json(); session=result['sessionId']
        with sqlite3.connect(self.database) as db: db.execute("UPDATE orders SET created=created-7200,link_id='link123'")
        with patch.object(self.provider,'cancel_checkout',create=True) as cancel:
            self.tick(); cancel.assert_called_once_with('link123')
        self.assertEqual(self.client.get('/inventory').json()['items'][0]['available'],2)
        self.assertTrue(self.order(session)['cancelled'])
    def test_refund_prevents_further_production_and_revokes_downloads(self):
        result=self.checkout(self.quote().json()).json(); self.provider.is_paid=True; self.tick(); self.provider.is_paid=False; self.tick()
        status=self.client.post('/order',json={'sessionId':result['sessionId']}).json()
        self.assertFalse(status['paid']); self.assertEqual(status['downloads'],[])
        self.assertEqual(len(self.supplier.submitted),1)
        self.assertTrue(any(f['error'] for f in self.app.state.commerce.fulfillments(result['sessionId'])))

    def test_admin_cancel_releases_unpaid_office_reservations_only(self):
        items=[{'id':'office','qty':2}]
        result=self.checkout(self.quote(items).json(),items).json();session=result['sessionId'];ref=self.order(session)['request_id']
        with sqlite3.connect(self.database) as db: db.execute("UPDATE orders SET link_id='link123'")
        with patch.object(self.provider,'cancel_checkout',create=True) as cancel:
            response=self.admin('POST','/admin/orders/'+ref+'/cancel',{})
            self.assertEqual(response.status_code,200,response.text);cancel.assert_called_once_with('link123')
        self.assertEqual(self.client.get('/inventory').json()['items'][0]['available'],2)
        self.assertTrue(self.order(session)['cancelled'])
    def test_worker_recovers_square_timeout_without_customer_returning(self):
        from backend.square import PaymentUnavailable
        q=self.quote().json()
        with patch.object(self.provider,'create_checkout',side_effect=PaymentUnavailable('timeout')):
            result=self.checkout(q);self.assertEqual(result.status_code,503)
        self.tick()
        self.assertEqual(len(self.provider.created),1)
        with sqlite3.connect(self.database) as db:
            self.assertIsNotNone(db.execute('SELECT provider_id FROM orders').fetchone()[0])
        self.assertEqual(self.supplier.submitted,[])
    def test_inventory_reservation_is_rechecked_after_quote(self):
        items=[{'id':'office','qty':2}]
        q1=self.quote(items).json();q2=self.quote(items).json()
        self.assertEqual(self.checkout(q1,items).status_code,200)
        self.assertEqual(self.checkout(q2,items).status_code,409)


class SupplierRequestTests(unittest.TestCase):
    def test_shipping_and_orders_use_fixed_shop_and_no_order_on_quote(self):
        p=Printify('secret',123)
        with patch.object(p,'post',return_value={'standard':1500}) as send:
            self.assertEqual(p.quote_shipping([{'product_id':'hoodie','variant_id':1,'quantity':1}],ADDRESS),1500)
            self.assertTrue(send.call_args.args[0].endswith('/orders/shipping.json'))
        with patch.object(p,'post',return_value={'express':100}):
            with self.assertRaises(PrintifyUnavailable): p.quote_shipping([],ADDRESS)
    def test_mixed_square_checkout_has_itemized_prices_shipping_and_idempotency(self):
        square=Square('secret','location','live')
        order={'request_id':'ref','quote_id':'quote','amount':4599,'shipping':600,'address':ADDRESS,
               'items':[{'name':'Hoodie','qty':1,'cents':3999,'label':'Black / S'}]}
        with patch.object(square,'request',return_value={'payment_link':{'id':'link','order_id':'squareorder','url':'https://square.link/u/test'}}) as send:
            result=square.create_checkout(order,'https://roddy.world/order.html#session_id=test')
        payload=send.call_args.args[2]
        self.assertEqual(payload['order']['line_items'][0]['base_price_money']['amount'],3999)
        self.assertEqual(payload['order']['service_charges'][0]['amount_money']['amount'],600)
        self.assertNotIn('shipping_fee',payload['checkout_options'])
        self.assertFalse(payload['checkout_options']['ask_for_shipping_address'])
        self.assertEqual(payload['idempotency_key'],'ref'); self.assertEqual(result[2],'link')

    def test_square_invalid_customer_email_has_actionable_safe_error(self):
        import httpx
        from backend.square import PaymentInputError
        response=httpx.Response(400,json={'errors':[{'code':'INVALID_EMAIL_ADDRESS','detail':'private provider payload'}]},request=httpx.Request('POST','https://connect.squareup.com'))
        with patch('backend.square.httpx.request',return_value=response):
            with self.assertRaises(PaymentInputError) as exc:
                Square('secret','location','live').request('POST','/v2/online-checkout/payment-links',{})
        self.assertIn('email address',str(exc.exception));self.assertNotIn('private',str(exc.exception))
