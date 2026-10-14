import copy,io,json,sqlite3,unittest,zipfile
from fastapi import HTTPException
from backend import test_commerce as base
from backend.aliexpress_quotes import AliExpressQuotes
from backend.supplier_quotes import MouserQuotes

class ReadOnlyQuotes(unittest.TestCase):
    def test_mouser_search_only_checks_quantity_price_and_shipping(self):
        adapter=MouserQuotes({'searchKey':'test'},lambda *_:None)
        adapter.client.product=lambda *_:{'minimumQuantity':2,'orderMultiple':2,'availableQuantity':10,'priceBreaks':[{'quantity':1,'currency':'USD','costCents':500},{'quantity':4,'currency':'USD','costCents':450}]}
        item={'supplier':{'supplierSku':'123-PART'},'qty':4,'cents':999,'officeShipping':{'US':{'firstItem':10,'additionalItem':1}}}
        result=adapter.quote(item,{'country':'US'})
        self.assertEqual(result['unitCostCents'],450);self.assertEqual(result['shippingCents'],1300)
        for invalid in [{**item,'qty':3},{**item,'qty':12},{**item,'cents':100},{**item,'officeShipping':{}}]:
            with self.assertRaises(HTTPException):adapter.quote(invalid,{'country':'US'})

    def test_stock_and_shipping_quotes_do_not_submit_or_pay(self):
        adapter=AliExpressQuotes({'appKey':'test','appSecret':'test','accessToken':'test'})
        calls=[]
        def call(method,payload,authorized):
            calls.append(method)
            if method=='aliexpress.ds.product.get':return {'result':{'ae_store_info':{'store_id':'store'},'ae_item_sku_info_dtos':[{'sku_id':'sku','currency_code':'USD','sku_available_stock':'4','offer_sale_price':'68.39','sku_attr':'14:1'}]}}
            self.assertEqual(method,'aliexpress.ds.freight.query')
            return {'result':{'success':True,'delivery_options':[{'shipping_fee_currency':'USD','shipping_fee_cent':'1.99','tracking':True,'code':'TRACKED'}]}}
        adapter.client.call=call
        item={'supplier':{'supplierSku':'12345','variantId':'sku','sellerId':'store'},'qty':1,'cents':9999}
        q=adapter.quote(item,{'country':'US','region':'NY'})
        self.assertEqual(q['shippingCents'],199);self.assertEqual(q['totalCents'],7038)
        self.assertEqual(calls,['aliexpress.ds.product.get','aliexpress.ds.freight.query'])
        self.assertFalse(hasattr(adapter,'submit'))
        with self.assertRaises(HTTPException):adapter.quote({**item,'qty':5},{'country':'US','region':'NY'})

class ManualSupplierOrderTests(unittest.TestCase):
    quote=base.MixedCheckoutTests.quote
    checkout=base.MixedCheckoutTests.checkout
    order=base.MixedCheckoutTests.order
    tick=base.MixedCheckoutTests.tick
    admin=base.MixedCheckoutTests.admin
    def setUp(self):
        base.MixedCheckoutTests.setUp(self)
        class QuoteOnly:
            calls=0
            def quote(inner,item,address):
                inner.calls+=1
                return {'unitCostCents':6839,'shippingCents':199,'totalCents':6839*item['qty']+199,'currency':'USD','service':'TRACKED','skuAttr':'14:1'}
        self.quotes=QuoteOnly();self.app.state.commerce.supplier_quote_factory=lambda kind:self.quotes
        self.product={'id':'supplier-keyboard','name':'Keyboard','price':99.99,'type':'physical','active':True,'status':'available','trackStock':False,'supplier':{'provider':'aliexpress','supplierSku':'12345678','variantId':'87654321','sellerId':'store','productUrl':'https://www.aliexpress.com/item/12345678.html','fulfillment':'manual'},'officeShipping':{}}
        self.catalog['products'].append(self.product);self.items=[{'id':self.product['id'],'qty':1}]
    def test_verified_payment_creates_manual_queue_and_private_details_never_places_order(self):
        q=self.quote();self.assertEqual(q.status_code,200,q.text);self.assertEqual(q.json()['shipping'],199)
        result=self.checkout(q.json());self.assertEqual(result.status_code,200,result.text)
        self.tick();self.assertEqual(self.app.state.commerce.fulfillments(result.json()['sessionId']),[])
        self.provider.is_paid=True;self.tick();order=self.order(result.json()['sessionId'])
        self.assertEqual(self.app.state.commerce.fulfillments(order['session'])[0]['state'],'ready-to-order')
        public=self.client.post('/order',json={'sessionId':order['session']});self.assertEqual(public.status_code,200)
        for secret in ['aliexpress','mouser','printify','supplierId','supplierSku','87654321']:self.assertNotIn(secret,public.text)
        path='/admin/orders/'+order['request_id']+'/supplier'
        self.assertEqual(self.client.post(path,json={'action':'download','kind':'aliexpress'}).status_code,401)
        packet=self.admin('POST',path,{'action':'download','kind':'aliexpress'});self.assertEqual(packet.status_code,200,packet.text[:100])
        with zipfile.ZipFile(io.BytesIO(packet.content)) as archive:
            detail=json.loads(archive.read('ORDER_DETAILS.json'));self.assertEqual(detail['delivery'],base.ADDRESS);self.assertEqual(detail['items'][0]['supplier']['variantId'],'87654321')
        self.assertEqual(self.admin('POST',path,{'action':'ordered','kind':'aliexpress','supplierReference':'ALI-01'}).status_code,200)
        self.assertEqual(self.app.state.commerce.fulfillments(order['session'])[0]['state'],'submitted')
        ship=self.admin('POST','/admin/orders/'+order['request_id']+'/shipment',{'kind':'aliexpress','carrier':'UPS','number':'TRACK-1','url':'https://www.ups.com/'})
        self.assertEqual(ship.status_code,200,ship.text);self.assertEqual(self.app.state.commerce.fulfillments(order['session'])[0]['state'],'shipped')
        self.assertEqual(self.admin('POST',path,{'action':'pending','kind':'aliexpress'}).status_code,409)
        self.assertEqual(self.admin('GET','/admin/orders?view=shipped').json()['total'],1)
    def test_expenses_exports_and_finance_are_owner_only(self):
        for path in ['/admin/orders/export','/admin/orders/sync']:
            self.assertEqual(self.client.post(path,json={}).status_code,401)
        q=self.quote().json();result=self.checkout(q).json();self.provider.is_paid=True;self.tick();order=self.order(result['sessionId'])
        expense=self.admin('POST','/admin/orders/'+order['request_id']+'/expenses',{'supplier':'AliExpress','reference':'ALI-01','amountCents':7038,'currency':'USD','date':'2026-10-14'})
        self.assertEqual(expense.status_code,200,expense.text)
        csv=self.admin('POST','/admin/orders/export',{'kind':'expenses'});self.assertEqual(csv.status_code,200);self.assertIn('70.38',csv.text)
    def test_mouser_manual_orders_use_same_queue_without_order_api_access(self):
        self.product['supplier'].update(provider='mouser',supplierSku='123-PART',variantId='')
        q=self.quote();self.assertEqual(q.status_code,200,q.text);result=self.checkout(q.json()).json();self.provider.is_paid=True;self.tick()
        self.assertEqual(self.app.state.commerce.fulfillments(result['sessionId'])[0]['kind'],'mouser')
        self.assertEqual(self.app.state.commerce.fulfillments(result['sessionId'])[0]['state'],'ready-to-order')
