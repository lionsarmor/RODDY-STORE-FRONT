import csv
import io
import json
import sqlite3
import unittest
from unittest.mock import patch
from uuid import uuid4

from backend import test_checkout as checkout_tests


class FreeDownloadTests(unittest.TestCase):
    setUp_checkout = checkout_tests.CheckoutTests.setUp
    make_client = checkout_tests.CheckoutTests.make_client
    checkout = checkout_tests.CheckoutTests.checkout
    status = checkout_tests.CheckoutTests.status

    def setUp(self):
        self.setUp_checkout()
        self.catalog['products'].append({'id':'free-game','name':'Free game','type':'digital','active':True,
            'status':'available','price':0,'trackStock':False,'downloadUrl':'https://roddy.world/downloads/game.zip',
            'videoEditions':[{'name':'X16 edition','downloads':[{'label':'X16 movie','url':'https://roddy.world/downloads/movie.zip'}]}]})
        self.body={'requestId':str(uuid4()),'productId':'free-game','email':' Sam@Example.com ',
                   'downloadUrl':'https://roddy.world/downloads/game.zip','firstName':'Sam'}
        self.origin={'origin':'https://roddy.world'}

    def free(self, **changes):
        return self.client.post('/free-downloads',json={**self.body,**changes},headers=self.origin)

    def admin(self, path='/admin/orders', body=None):
        response=type('Response',(),{'raise_for_status':lambda _:None,'json':lambda _:{'login':'lionsarmor'}})()
        with patch('backend.app.httpx.get',return_value=response):
            return self.client.request('GET' if body is None else 'POST',path,json=body,headers={'authorization':'Bearer owner'})

    def test_email_required_and_only_published_free_files_can_create_orders(self):
        self.assertEqual(self.client.post('/free-downloads',json=self.body).status_code,403)
        for changes in [{'email':''},{'email':'invalid'},{'downloadUrl':'https://evil.example/file.zip'},
                        {'downloadUrl':['bad']},{'requestId':'guessable'},{'newsletterConsent':'yes'},{'company':'spam'}]:
            self.assertEqual(self.free(**changes).status_code,400,changes)
        self.assertEqual(self.free(productId='desk').status_code,409)
        self.catalog['products'][-1]['price']=1
        self.assertEqual(self.free().status_code,409)
        with sqlite3.connect(self.database) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM orders').fetchone()[0],0)

    def test_free_order_has_email_zero_revenue_and_idempotent_download_start(self):
        response=self.free();self.assertEqual(response.status_code,200,response.text)
        link=response.json();self.assertEqual(self.free().status_code,200)
        self.assertEqual(self.free(email='different@example.com').status_code,409)
        orders=self.admin().json();self.assertEqual(orders['total'],1)
        order=orders['data'][0]
        self.assertEqual(order['payment_status'],'free');self.assertEqual(order['amount_total'],0)
        self.assertEqual(order['address']['email'],'sam@example.com')
        self.assertEqual(order['fulfillments'],[]);self.assertIsNone(order['downloadOpenedAt'])
        path=link['url'].removeprefix('https://api.example.test')
        first=self.client.get(path,follow_redirects=False)
        self.assertEqual(first.status_code,303);self.assertEqual(first.headers['location'],self.body['downloadUrl'])
        self.assertEqual(first.headers['referrer-policy'],'no-referrer')
        self.client.get(path,follow_redirects=False)
        orders=self.admin('/admin/orders?view=free').json()
        self.assertEqual(orders['summary']['free'],1);self.assertEqual(orders['summary']['freeStarted'],1)
        self.assertEqual(orders['summary']['capturedCents'],0);self.assertIsNotNone(orders['data'][0]['downloadOpenedAt'])
        self.assertEqual(self.provider.created,[])
        with sqlite3.connect(self.database) as db:
            db.execute('UPDATE free_download_tickets SET expires=0')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM free_download_receipts').fetchone()[0],1)
        self.assertEqual(self.client.get(path,follow_redirects=False).status_code,410)

    def test_worker_never_creates_checkout_or_supplier_work_for_zero_orders(self):
        self.assertEqual(self.free().status_code,200)
        commerce=self.client.app.state.commerce
        with patch.object(commerce,'recover') as recover, patch.object(self.provider,'paid') as paid:
            commerce.tick();recover.assert_not_called();paid.assert_not_called()
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sale_events').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM fulfillments').fetchone()[0],0)

    def test_newsletter_is_optional_and_never_reactivates_suppressed_addresses(self):
        self.assertEqual(self.free().status_code,200)
        with sqlite3.connect(self.database) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM newsletter_subscribers').fetchone()[0],0)
        self.assertEqual(self.free(requestId=str(uuid4()),newsletterConsent=True).status_code,200)
        with sqlite3.connect(self.database) as db:
            row=db.execute('SELECT email,status,source FROM newsletter_subscribers').fetchone()
            self.assertEqual(row,('sam@example.com','active','free-download'))
            db.execute("UPDATE newsletter_subscribers SET status='unsubscribed'")
        self.free(requestId=str(uuid4()),newsletterConsent=True)
        with sqlite3.connect(self.database) as db:self.assertEqual(db.execute('SELECT status FROM newsletter_subscribers').fetchone()[0],'unsubscribed')

    def test_edition_and_paid_revenue_are_preserved_in_records_and_exports(self):
        session=self.checkout().json()['sessionId'];self.provider.is_paid=True;self.status(session)
        self.free(downloadUrl='https://roddy.world/downloads/movie.zip')
        data=self.admin('/admin/orders?status=free').json()
        self.assertEqual(data['total'],1);self.assertIn('X16 edition',data['data'][0]['items'][0]['label'])
        self.assertEqual(data['summary']['capturedCents'],399)
        exported=self.admin('/admin/orders/export',{'kind':'orders'}).content.decode('utf-8-sig')
        rows=list(csv.DictReader(io.StringIO(exported)))
        self.assertEqual(len(rows),2)
        free=next(r for r in rows if r['payment_status']=='free')
        self.assertEqual(free['order_total'],'0.00');self.assertEqual(free['customer_email'],'sam@example.com')

    def test_free_customer_can_receive_thank_you_and_fresh_download_without_new_order(self):
        self.free();order=self.admin().json()['data'][0]
        response=self.admin('/admin/orders/'+order['id']+'/downloads',{'productId':'free-game','purpose':'share'})
        self.assertEqual(response.status_code,200,response.text)
        path=response.json()['url'].removeprefix('https://api.example.test')
        self.assertEqual(self.client.get(path,follow_redirects=False).status_code,303)
        body={'subject':'Thanks for downloading!','body':'Enjoy your game!','context':order['messageContext'],'confirmedSent':True}
        saved=self.admin('/admin/orders/'+order['id']+'/messages',body)
        self.assertEqual(saved.status_code,200,saved.text)
        current=self.admin().json();self.assertEqual(current['total'],1)
        self.assertEqual(current['data'][0]['messages'][0]['recipient'],'sam@example.com')
