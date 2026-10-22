"""Alpha access is checked on the server and private files remain ticketed."""
import hashlib
import json
import sqlite3
import unittest
from uuid import uuid4
from unittest.mock import patch
from backend import test_free_downloads as free_tests


class BetaDownloadTests(unittest.TestCase):
    setUp_checkout = free_tests.FreeDownloadTests.setUp_checkout
    make_client = free_tests.FreeDownloadTests.make_client
    free = free_tests.FreeDownloadTests.free
    admin = free_tests.FreeDownloadTests.admin

    def setUp(self):
        self.setUp_checkout()
        self.code = 'COWABUNGA-TEST-ONLY'
        self.catalog['products'].append({'id':'buddy','name':'BUDDY','type':'digital','active':True,'status':'coming-soon',
            'price':0,'trackStock':False,'betaAccess':True,'softwareEditions':[
                {'id':'dos','name':'DOS','downloadable':True}, {'id':'x16','name':'X16','downloadable':True},
                {'id':'not-ready','name':'Not ready','downloadable':False}]})
        self.manifest['buddy']={'beta':{'codeHash':hashlib.sha256(self.code.encode()).hexdigest(),
            'editions':{'dos':dict(self.manifest['desk']),'x16':dict(self.manifest['desk'])}}}
        self.body={'requestId':str(uuid4()),'productId':'buddy','email':'alpha@example.com','editionId':'dos','testerCode':self.code}
        self.origin={'origin':'https://roddy.world'}

    def test_codes_are_required_even_when_a_public_download_url_is_supplied(self):
        for code in ['', None, 'wrong', ['bad'], 'A'*121]:
            response=self.free(testerCode=code,downloadUrl='https://roddy.world/fake.zip')
            self.assertEqual(response.status_code,403,response.text)
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM orders').fetchone()[0],0)
        self.assertEqual(self.provider.created,[])

    def test_valid_code_serves_private_snapshot_and_creates_zero_order(self):
        response=self.free(testerCode='  cowabunga-test-only  ')
        self.assertEqual(response.status_code,200,response.text)
        data=response.json();path=data['url'].removeprefix('https://api.example.test')
        self.assertNotIn('sha256',response.text);self.assertNotIn(self.code,response.text)
        with patch.object(self.provider,'paid',side_effect=AssertionError('No payment for alpha')):
            file=self.client.get(path,follow_redirects=False)
        self.assertEqual(file.status_code,200);self.assertEqual(file.content,self.zip.read_bytes())
        self.assertEqual(file.headers['content-type'],'application/zip')
        self.assertEqual(file.headers['cache-control'],'no-store')
        order=self.admin().json()['data'][0]
        self.assertEqual(order['payment_status'],'free');self.assertEqual(order['amount_total'],0)
        self.assertEqual(order['items'][0]['label'],'DOS · Alpha');self.assertIsNotNone(order['downloadOpenedAt'])
        self.assertNotIn(self.code,json.dumps(order));self.assertNotIn('sha256',json.dumps(order));self.assertNotIn(str(self.root),json.dumps(order))
        with sqlite3.connect(self.database) as db:
            snapshot=db.execute('SELECT cart,items,address FROM orders').fetchone()
            self.assertNotIn(self.code,str(snapshot));self.assertNotIn('testerCode',str(snapshot))

    def test_each_edition_has_its_own_order_and_requests_are_idempotent(self):
        self.assertEqual(self.free().status_code,200)
        self.assertEqual(self.free().status_code,200)
        self.assertEqual(self.free(editionId='x16').status_code,409)
        self.assertEqual(self.free(requestId=str(uuid4()),editionId='x16').status_code,200)
        self.assertEqual(self.admin().json()['summary']['free'],2)
        self.assertEqual(self.admin().json()['summary']['capturedCents'],0)

    def test_unpublished_and_unknown_editions_cannot_be_downloaded(self):
        for edition in ['unknown','not-ready','../desk',None]:
            self.assertEqual(self.free(editionId=edition).status_code,400)
        self.catalog['products'][-1]['active']=False
        self.assertEqual(self.free().status_code,409)

    def test_paid_free_flag_or_sold_out_products_cannot_bypass_access(self):
        self.assertEqual(self.free(productId='desk').status_code,409)
        p=self.catalog['products'][-1]
        for changes in [{'price':1},{'trackStock':True},{'pricePending':True},{'status':'sold-out'},{'betaAccess':False}]:
            previous=dict(p);p.update(changes)
            self.assertEqual(self.free().status_code,409,changes)
            p.clear();p.update(previous)

    def test_ticket_expiry_and_file_integrity_are_enforced(self):
        link=self.free().json()['url'].removeprefix('https://api.example.test')
        self.zip.write_bytes(b'changed')
        self.assertEqual(self.client.get(link).status_code,503)
        self.assertEqual(self.free(requestId=str(uuid4())).status_code,503)
        with sqlite3.connect(self.database) as db:
            db.execute('UPDATE free_download_tickets SET expires=0')
        self.assertEqual(self.client.get(link).status_code,410)

    def test_admin_can_reissue_alpha_without_code_or_new_order(self):
        self.free();ref=self.admin().json()['data'][0]['id']
        # Support links authorize the exact ordered snapshot even after a code rotation.
        self.manifest['buddy']['beta']['codeHash']=hashlib.sha256(b'NEW-CODE').hexdigest()
        response=self.admin('/admin/orders/'+ref+'/downloads',{'productId':'buddy','purpose':'share'})
        self.assertEqual(response.status_code,200,response.text)
        data=response.json();link=data.get('downloads',[data])[0]
        self.assertEqual(self.client.get(link['url'].removeprefix('https://api.example.test')).content,self.zip.read_bytes())
        self.assertEqual(self.admin().json()['total'],1)

    def test_invalid_attempts_are_rate_limited(self):
        for i in range(10):self.assertEqual(self.free(testerCode='bad').status_code,403)
        self.assertEqual(self.free().status_code,429)
