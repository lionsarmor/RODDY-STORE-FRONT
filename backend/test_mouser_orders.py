import copy,json,unittest
from unittest.mock import patch
from uuid import uuid4
import httpx
from fastapi import HTTPException
from backend import test_commerce as base
ADDRESS=base.ADDRESS
from backend.mouser_orders import MouserOrders,shipping_address,money

class Transport:
    def __init__(self):
        self.carts={};self.orders={};self.submissions=0;self.calls=[];self.cost=5.0;self.shipping=8.0
        self.timeout=False;self.hide_history=False;self.wrong_address=False;self.stock=100
    def __call__(self,method,url,params,json,timeout):
        path=url.split('/api/v1/')[1];self.calls.append((method,path,copy.deepcopy(json)))
        if path=='cart/items/insert':
            key=str(uuid4());self.carts[key]=json['CartItems'];data={'CartKey':key,'CurrencyCode':'USD','Errors':[]}
        elif path=='order/options/query':
            data={'OrderInitialize':{'CurrencyCode':'USD','Errors':[],
                'Payment':{'PaymentTypes':[{'Method':31,'Name':'Visa Exp 12/99','CreditCardLastFourDigits':'1111'}]},
                'Shipping':{'Methods':[{'Code':1,'Method':'UPS Ground','Rate':self.shipping},{'Code':73,'Method':'UPS Ground - Bill Recipient','Rate':0}]}}}
        elif path=='order':
            body=json['Order'];dest=copy.deepcopy(body['ShippingAddress']);lines=self.carts[body['CartKey']]
            if self.wrong_address:dest['AddressOne']='A different destination'
            merchandise=sum(self.cost*l['Quantity'] for l in lines)
            result={'CurrencyCode':'USD','OrderID':'0','SubmitOrder':False,'ShippingAddress':dest,'Errors':[],
                'OrderTotal':round(merchandise+self.shipping+.5,2),'MerchandiseTotal':merchandise,'TaxAmount':.5,
                'ShippingMethod':{'PrimaryCode':1,'PrimaryShippingRate':self.shipping,'SecondaryCode':0,'SecondaryShippingRate':-1.0},
                'OrderLines':[{**l,'MouserATS':self.stock,'ExtendedPrice':self.cost*l['Quantity'],'Errors':[]} for l in lines]}
            if body['SubmitOrder']:
                self.submissions+=1;ident=str(7000+self.submissions);result.update(OrderID=ident,SubmitOrder=True)
                self.orders[ident]={'WebOrderId':int(ident),'CurrencyCode':'USD','OrderStatusName':'Processing',
                    'PaymentDetail':{'PoNumber':body['Payment']['PoNumber']},'ShippingAddress':dest,
                    'OrderLines':[{'Quantity':l['Quantity'],'ProductInfo':{'MouserPartNumber':l['MouserPartNumber']}} for l in lines],
                    'SummaryDetail':{'OrderTotal':str(result['OrderTotal'])},'DeliveryDetail':{'TrackingDetails':[]}}
                if self.timeout:raise httpx.ReadTimeout('test-only')
            data={'Order':result}
        elif path=='orderhistory/ByDateFilter':
            data={'Errors':[],'OrderHistoryItems':[] if self.hide_history else [{'PoNumber':o['PaymentDetail']['PoNumber'],'WebOrderNumber':ident} for ident,o in self.orders.items()]}
        elif path=='orderhistory/webOrderNumber':data=self.orders[params['webOrderNumber']]
        else:raise AssertionError(path)
        return httpx.Response(200,json=data)

class MouserAutomaticTests(unittest.TestCase):
    quote=base.MixedCheckoutTests.quote;checkout=base.MixedCheckoutTests.checkout;order=base.MixedCheckoutTests.order
    tick=base.MixedCheckoutTests.tick;admin=base.MixedCheckoutTests.admin
    def setUp(self):
        base.MixedCheckoutTests.setUp(self)
        self.transport=Transport();self.patch=patch('backend.mouser_orders.httpx.request',side_effect=self.transport);self.patch.start();self.addCleanup(self.patch.stop)
        self.config={'orderKey':'test-only-key','automaticOrdering':True}
        self.app.state.commerce.mouser_factory=lambda:MouserOrders(self.config,lambda _:None)
        self.product={'id':'mouser-part','name':'Part','price':19.99,'type':'physical','active':True,'status':'available','trackStock':False,
            'supplier':{'provider':'mouser','supplierSku':'123-PART','fulfillment':'automatic'}}
        self.catalog['products'].append(self.product);self.items=[{'id':'mouser-part','qty':1}]
    def paid_order(self):
        q=self.quote();self.assertEqual(q.status_code,200,q.text)
        c=self.checkout(q.json());self.assertEqual(c.status_code,200,c.text)
        self.provider.is_paid=True
        return self.order(c.json()['sessionId'])
    def test_paid_order_direct_shipping_cost_record_and_tracking(self):
        q=self.quote();self.assertEqual(q.json()['subtotal'],1999);self.assertEqual(q.json()['shipping'],800)
        result=self.checkout(q.json());self.assertEqual(result.status_code,200,result.text)
        self.tick();self.assertEqual(self.transport.submissions,0)
        self.provider.is_paid=True;self.tick();order=self.order(result.json()['sessionId'])
        fs=self.app.state.commerce.fulfillments(order['session']);self.assertEqual(fs[0]['state'],'submitted');self.assertTrue(fs[0]['automatic'])
        self.assertEqual(self.transport.submissions,1)
        payload=next(c[2]['Order'] for c in self.transport.calls if c[1]=='order' and c[2]['Order']['SubmitOrder'])
        self.assertEqual(payload['ShippingAddress'],shipping_address(ADDRESS));self.assertEqual(payload['PrimaryShipping'],{'Code':1})
        self.tick();self.assertEqual(self.transport.submissions,1)
        expenses=self.app.state.commerce.records.expenses(order['session']);self.assertEqual(len(expenses),1);self.assertEqual(expenses[0]['amount'],1350)
        upstream=self.transport.orders['7001'];upstream['OrderStatusName']='Shipped';upstream['DeliveryDetail']={'ShippingMethodName':'UPS','TrackingDetails':[{'Number':'TRACK','Link':'https://www.ups.com/track'}]}
        self.tick();f=self.app.state.commerce.fulfillments(order['session'])[0];self.assertEqual(f['state'],'shipped');self.assertEqual(f['shipments'][0]['number'],'TRACK')
        admin=self.admin('GET','/admin/orders?view=all');self.assertEqual(admin.json()['total'],1)
        self.assertIn('7001',admin.text)
        for action in ['pending','ordered']:
            self.assertEqual(self.admin('POST','/admin/orders/'+order['request_id']+'/supplier',{'kind':'mouser','action':action,'supplierReference':'manual'}).status_code,409)
        customer=self.client.post('/order',json={'sessionId':order['session']})
        for secret in ['test-only-key','1111','123-PART','supplierId','procurement']:self.assertNotIn(secret,customer.text)
    def test_timeout_never_resubmits_and_reconciles_original(self):
        order=self.paid_order();self.transport.timeout=True;self.transport.hide_history=True
        self.tick();self.assertEqual(self.transport.submissions,1)
        for _ in range(3):self.tick()
        self.assertEqual(self.transport.submissions,1);self.assertEqual(self.app.state.commerce.fulfillments(order['session'])[0]['state'],'review')
        self.transport.hide_history=False;self.tick()
        self.assertEqual(self.transport.submissions,1);self.assertEqual(self.app.state.commerce.fulfillments(order['session'])[0]['supplierId'],'7001')
    def test_cost_increase_flags_paid_order_and_suspends_product(self):
        order=self.paid_order();self.transport.cost=25;self.tick()
        self.assertEqual(self.transport.submissions,0)
        self.assertEqual(self.app.state.commerce.fulfillments(order['session'])[0]['state'],'review')
        self.assertEqual(self.admin('GET','/admin/orders?view=inbox').json()['total'],1)
        public=self.client.get('/inventory').json();self.assertEqual(public['suspendedProducts'],['mouser-part']);self.assertNotIn('reason',json.dumps(public))
        self.assertEqual(self.quote().status_code,409)
        self.product['price']=39.99
        self.assertEqual(self.quote().status_code,409,'Changing retail does not silently clear a hold')
        self.assertEqual(self.admin('POST','/admin/fulfillment-holds/mouser-part',{'action':'clear'}).status_code,200)
        self.assertEqual(self.quote().status_code,200)
        self.tick();self.assertEqual(self.transport.submissions,0,'Old paid orders retain original quote and review status')
    def test_mixed_cart_has_one_mouser_shipping_charge_and_exact_quantities(self):
        second=copy.deepcopy(self.product);second.update(id='mouser-second');second['supplier']['supplierSku']='456-SECOND';self.catalog['products'].append(second)
        self.items=[{'id':'mouser-part','qty':2},{'id':'mouser-second','qty':3}]
        q=self.quote();self.assertEqual(q.status_code,200,q.text);self.assertEqual(q.json()['shipping'],800)
        result=self.checkout(q.json());self.assertEqual(result.status_code,200,result.text);self.provider.is_paid=True;self.tick()
        self.assertEqual(self.transport.submissions,1)
        self.assertEqual(sum(l['Quantity'] for l in self.transport.orders['7001']['OrderLines']),5)
    def test_refund_disabled_account_stock_and_address_do_not_submit(self):
        order=self.paid_order();self.provider.is_paid=False;self.tick();self.assertEqual(self.transport.submissions,0)
        self.provider.is_paid=True;self.config['automaticOrdering']=False;self.tick();self.assertEqual(self.transport.submissions,0)
        self.assertEqual(self.quote().status_code,409)
        self.config['automaticOrdering']=True;self.transport.wrong_address=True;self.assertEqual(self.quote().status_code,409)
        self.transport.wrong_address=False;self.transport.stock=0;self.assertEqual(self.quote().status_code,409)
        self.assertEqual(self.transport.submissions,0)
    def test_subcent_prices_and_provider_neutral_suspensions(self):
        self.assertEqual(money('0.0049'),0);self.assertEqual(money('0.005'),1)
        for provider in ['mouser','printify','aliexpress','yuzu']:
            self.app.state.commerce.holds.suspend([{'id':'part-'+provider,'kind':provider}],'private cost overrun')
        self.assertEqual(len(self.admin('GET','/admin/fulfillment-holds').json()['items']),4)
        self.assertEqual(self.client.post('/admin/fulfillment-holds/part-yuzu',json={'action':'clear'}).status_code,401)
