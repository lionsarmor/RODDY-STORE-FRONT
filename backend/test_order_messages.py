import unittest
from backend import test_commerce as commerce_tests


class OrderMessageTests(unittest.TestCase):
    quote=commerce_tests.MixedCheckoutTests.quote
    checkout=commerce_tests.MixedCheckoutTests.checkout
    order=commerce_tests.MixedCheckoutTests.order
    tick=commerce_tests.MixedCheckoutTests.tick
    admin=commerce_tests.MixedCheckoutTests.admin

    def setUp(self):
        commerce_tests.MixedCheckoutTests.setUp(self)
        self.items=[{'id':'office','qty':1}]

    def paid(self):
        quote=self.quote();self.assertEqual(quote.status_code,200,quote.text)
        result=self.checkout(quote.json());self.assertEqual(result.status_code,200,result.text)
        self.provider.is_paid=True;self.tick()
        return self.order(result.json()['sessionId'])

    def message(self, order):
        return {'subject':'Thank you, your order shipped','body':'Thank you!\nUSPS: TRACK-1','context':self.app.state.commerce.records.message_context(order),'confirmedSent':True}

    def test_owner_confirmation_required_idempotent_and_kept_with_order(self):
        order=self.paid();path='/admin/orders/'+order['request_id']+'/messages';body=self.message(order)
        self.assertEqual(self.client.post(path,json=body).status_code,401)
        self.assertEqual(self.admin('POST',path,{**body,'confirmedSent':False}).status_code,400)
        first=self.admin('POST',path,body);self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(self.admin('POST',path,body).json()['id'],first.json()['id'])
        listed=self.admin('GET','/admin/orders?view=all').json()['data'][0]
        self.assertEqual(len(listed['messages']),1)
        self.assertEqual(listed['messages'][0]['recipient'],'buyer@example.com')
        self.assertEqual(listed['messages'][0]['body'],body['body'])
        self.assertEqual(listed['messageContext'],body['context'])
        self.assertEqual(self.supplier.submitted,[])

    def test_changed_tracking_rejects_stale_draft_preserves_previous_confirmation(self):
        order=self.paid();path='/admin/orders/'+order['request_id']+'/messages';body=self.message(order)
        self.assertEqual(self.admin('POST',path,body).status_code,200)
        shipment={'kind':'office','carrier':'USPS','number':'TRACK-2','url':'https://tools.usps.com/'}
        self.assertEqual(self.admin('POST','/admin/orders/'+order['request_id']+'/shipment',shipment).status_code,200)
        self.assertEqual(self.admin('POST',path,body).status_code,409)
        updated=self.message(order);self.assertNotEqual(updated['context'],body['context'])
        updated['body']='Updated tracking: TRACK-2'
        self.assertEqual(self.admin('POST',path,updated).status_code,200)
        self.assertEqual(len(self.app.state.commerce.records.messages(order['session'])),2)
        self.app.state.commerce.update(order['session'],'office','delivered',shipments=[{**shipment,'deliveredAt':'today'}])
        self.assertEqual(self.message(order)['context'],updated['context'])

    def test_unpaid_refunded_and_header_injection_are_rejected(self):
        order=self.paid();path='/admin/orders/'+order['request_id']+'/messages';body=self.message(order)
        self.assertEqual(self.admin('POST',path,{**body,'subject':'Hi\r\nBcc: someone@example.com'}).status_code,400)
        with self.app.state.commerce.connect() as db:db.execute('UPDATE orders SET paid=0 WHERE session=?',(order['session'],))
        self.assertEqual(self.admin('POST',path,body).status_code,409)

    def test_sale_queue_counts_all_manual_order_kinds_once(self):
        order=self.paid();sales=self.admin('GET','/admin/sales').json();self.assertEqual(sales['pendingOrders'],1);self.assertEqual(sales['pendingKeycaps'],0)
        self.app.state.commerce.update(order['session'],'office','shipped',shipments=[])
        self.assertEqual(self.admin('GET','/admin/sales').json()['pendingOrders'],0)
