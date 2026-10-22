import hashlib
import json
import sqlite3
import time
import unittest
from unittest.mock import patch

from backend import test_checkout as checkout_tests


class AdminDownloadTests(unittest.TestCase):
    setUp = checkout_tests.CheckoutTests.setUp
    make_client = checkout_tests.CheckoutTests.make_client
    checkout = checkout_tests.CheckoutTests.checkout
    status = checkout_tests.CheckoutTests.status

    def admin(self, reference, body=None, login='lionsarmor'):
        response = type('Response', (), {'raise_for_status': lambda _: None, 'json': lambda _: {'login': login}})()
        with patch('backend.app.httpx.get', return_value=response):
            return self.client.post('/admin/orders/' + reference + '/downloads', json=body or {'productId': 'desk'},
                                    headers={'authorization': 'Bearer owner-secret'})

    def purchase(self):
        result = self.checkout().json()
        with sqlite3.connect(self.database) as db:
            reference = db.execute('SELECT request_id FROM orders WHERE session=?', (result['sessionId'],)).fetchone()[0]
        return reference, result['sessionId']

    def download(self, link):
        return self.client.get(link['url'].removeprefix('https://api.example.test'))

    def test_only_owner_can_issue_links_and_listing_does_not_issue_them(self):
        reference, session = self.purchase()
        self.assertEqual(self.client.post('/admin/orders/' + reference + '/downloads', json={'productId': 'desk'}).status_code, 401)
        self.assertEqual(self.admin(reference, login='someone-else').status_code, 403)
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM tickets').fetchone()[0], 0)

    def test_owner_reissues_expired_receipt_with_original_purchased_file(self):
        reference, session = self.purchase()
        self.provider.is_paid = True
        with sqlite3.connect(self.database) as db:
            db.execute('UPDATE orders SET created=0 WHERE session=?', (session,))
        self.assertEqual(self.status(session).status_code, 410)
        self.manifest['desk']['file'] = 'NEW-EDITION.zip'
        now = int(time.time())
        response = self.admin(reference, {'productId': 'desk', 'purpose': 'share'})
        self.assertEqual(response.status_code, 200, response.text)
        link = response.json()
        self.assertTrue(now + 7 * 86400 <= link['expiresAt'] <= int(time.time()) + 7 * 86400)
        self.assertEqual(link['filename'], self.zip.name)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        downloaded = self.download(link)
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.content, self.zip.read_bytes())
        self.assertIn('attachment', downloaded.headers['content-disposition'])
        self.assertEqual(self.status(session).status_code, 410)
        ticket = link['url'].rsplit('/', 1)[1]
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute('SELECT digest FROM tickets').fetchone()[0], hashlib.sha256(ticket.encode()).hexdigest())
        for secret in [session, 'owner-secret', self.manifest['desk']['sha256'], str(self.root)]:
            self.assertNotIn(secret, response.text)

    def test_unpaid_cached_paid_and_refunded_orders_cannot_issue_or_use_links(self):
        reference, session = self.purchase()
        self.assertEqual(self.admin(reference).status_code, 409)
        self.provider.is_paid = True
        now = int(time.time())
        link = self.admin(reference).json()
        self.assertTrue(now + 900 <= link['expiresAt'] <= int(time.time()) + 900)
        self.assertEqual(self.download(link).status_code, 200)
        self.provider.is_paid = False
        self.assertEqual(self.admin(reference, {'productId': 'desk', 'purpose': 'share'}).status_code, 409)
        self.assertEqual(self.download(link).status_code, 403)

    def test_unknown_products_physical_items_and_invalid_purposes_are_rejected(self):
        reference, session = self.purchase()
        self.provider.is_paid = True
        self.assertEqual(self.admin('missing').status_code, 404)
        self.assertEqual(self.admin(reference, {'productId': 'not-purchased'}).status_code, 404)
        for purpose in ['forever', [], None]:
            self.assertEqual(self.admin(reference, {'productId': 'desk', 'purpose': purpose}).status_code, 400)
        with sqlite3.connect(self.database) as db:
            items = json.loads(db.execute('SELECT items FROM orders WHERE session=?', (session,)).fetchone()[0])
            items[0]['kind'] = 'office'
            db.execute('UPDATE orders SET items=? WHERE session=?', (json.dumps(items), session))
        self.assertEqual(self.admin(reference).status_code, 404)

    def test_expired_tickets_and_damaged_files_fail_closed(self):
        reference, session = self.purchase()
        self.provider.is_paid = True
        link = self.admin(reference, {'productId': 'desk', 'purpose': 'share'}).json()
        with sqlite3.connect(self.database) as db:
            db.execute('UPDATE tickets SET expires=0')
        self.assertEqual(self.download(link).status_code, 410)
        fresh = self.admin(reference).json()
        self.zip.write_bytes(b'wrong release')
        self.assertEqual(self.admin(reference).status_code, 503)
        self.assertEqual(self.download(fresh).status_code, 503)
