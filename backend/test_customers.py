import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import httpx

from fastapi.testclient import TestClient
from backend.app import create_app
from backend.test_checkout import FakeProvider


ADDRESS = dict(first_name='Alex', last_name='Example', email='alex@example.com',
               phone='5125550123', country='US', region='TX', address1='123 Test St',
               address2='', city='Austin', zip='78701')


class CustomerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / 'test.sqlite3'
        self.app = self.make_app()
        self.client = TestClient(self.app)
        self.origin = {'origin': 'https://roddy.world'}

    def make_app(self):
        return create_app(database=self.database, private_dir=self.root, manifest={},
                          provider=FakeProvider(), catalog_loader=lambda: {'products': []},
                          enabled=False, worker_enabled=False)

    def account(self, handle='Alex_Test'):
        r = self.client.post('/forum/register', headers=self.origin,
                             json={'handle': handle, 'password': 'my test password'})
        self.assertEqual(r.status_code, 200, r.text)
        return {**self.origin, 'authorization': 'Bearer '+r.json()['token']}

    def save_address(self, headers, **extra):
        return self.client.post('/customer/addresses', headers=headers,
                                json={'label': 'Home', 'address': ADDRESS, **extra})

    def test_guest_access_and_foreign_origins_cannot_read_or_write_addresses(self):
        self.assertEqual(self.client.get('/customer/me').status_code, 401)
        self.assertEqual(self.save_address(self.origin).status_code, 401)
        headers = self.account()
        self.assertEqual(self.save_address({**headers, 'origin': 'https://evil.example'}).status_code, 403)
        with patch('backend.app.httpx.get', side_effect=httpx.HTTPError('Not an admin token')):
            self.assertEqual(self.client.get('/admin/customers', headers=headers).status_code, 401)

    def test_profiles_addresses_persist_and_never_appear_in_public_forum(self):
        headers = self.account()
        r = self.client.post('/customer/me', headers=headers, json={'name':'Alex Private','email':'Alex@Example.com'})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()['email'], 'alex@example.com')
        r = self.save_address(headers)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()['addresses'][0]['default'])
        data = TestClient(self.make_app()).get('/customer/me', headers=headers)
        self.assertEqual(data.json()['addresses'][0]['address'], ADDRESS)
        self.assertEqual(data.headers['cache-control'], 'no-store')
        self.assertEqual(self.client.get('/forum/me', headers=headers).json(), {'handle':'Alex_Test'})
        self.assertNotIn('Private', self.client.get('/forum/topics').text)
        self.assertNotIn('recovery_digest', data.text)
        self.assertNotIn('password', data.text)

    def test_cross_account_ids_cannot_read_update_delete_or_change_default(self):
        first = self.account(); second = self.account('Other_Test')
        own = self.save_address(first).json()['id']
        self.assertEqual(self.client.get('/customer/me', headers=second).json()['addresses'], [])
        self.assertEqual(self.save_address(second, id=own, default=True).status_code, 404)
        self.assertEqual(self.client.post('/customer/addresses/'+own+'/delete', headers=second, json={}).status_code, 404)
        self.assertEqual(len(self.client.get('/customer/me', headers=first).json()['addresses']), 1)

    def test_default_switch_delete_and_address_limit(self):
        headers = self.account()
        first = self.save_address(headers).json()['id']
        second = self.save_address(headers, label='Work', default=True).json()['id']
        entries = self.client.get('/customer/me', headers=headers).json()['addresses']
        self.assertEqual(sum(x['default'] for x in entries), 1)
        self.assertEqual(entries[0]['id'], second)
        deleted = self.client.post('/customer/addresses/'+second+'/delete', headers=headers, json={})
        self.assertEqual(deleted.json()['addresses'][0]['id'], first)
        self.assertTrue(deleted.json()['addresses'][0]['default'])
        for n in range(9):
            self.assertEqual(self.save_address(headers, label=str(n)).status_code, 200)
        self.assertEqual(self.save_address(headers).status_code, 400)
        self.assertEqual(self.save_address(headers, id=first, label='New name').status_code, 200)

    def test_validation_rejects_incomplete_or_unsupported_destinations(self):
        headers = self.account()
        for changes in [{'country':'ZZ'}, {'region':'XX'}, {'email':'bad'}, {'zip':'not-a-zip'}, {'address1':'line\nbreak'}, {'city':''}]:
            self.assertEqual(self.save_address(headers, address={**ADDRESS, **changes}).status_code, 400)
        self.assertEqual(self.save_address(headers, default='yes').status_code, 400)
        self.assertEqual(self.save_address(headers, label='a'*41).status_code, 400)
        canada = {**ADDRESS, 'country':'CA', 'region':'ON', 'zip':'M5V 2T6'}
        self.assertEqual(self.save_address(headers, address=canada).status_code, 200)

    def test_single_use_recovery_code_hash_and_session_revocation(self):
        headers = self.account()
        bad = self.client.post('/customer/recovery-code', headers=headers, json={'password':'wrong password'})
        self.assertEqual(bad.status_code, 401)
        r = self.client.post('/customer/recovery-code', headers=headers, json={'password':'my test password'})
        self.assertEqual(r.status_code, 200, r.text)
        code = r.json()['recoveryCode']
        with sqlite3.connect(self.database) as db:
            stored = db.execute('SELECT recovery_digest FROM customer_profiles').fetchone()[0]
        self.assertEqual(stored, hashlib.sha256(code.encode()).hexdigest())
        payload = {'handle':'Alex_Test','recoveryCode':code,'newPassword':'a fresh password'}
        result = self.client.post('/customer/recover', headers=self.origin, json=payload)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(self.client.get('/customer/me', headers=headers).status_code, 401)
        self.assertEqual(self.client.post('/customer/recover', headers=self.origin, json=payload).status_code, 401)
        fresh = {**self.origin, 'authorization':'Bearer '+result.json()['token']}
        self.assertFalse(self.client.get('/customer/me', headers=fresh).json()['hasRecoveryCode'])

    def test_password_change_requires_current_password_and_revokes_sessions(self):
        headers = self.account()
        wrong = self.client.post('/customer/password', headers=headers, json={'password':'wrong password','newPassword':'a fresh password'})
        self.assertEqual(wrong.status_code, 401)
        good = self.client.post('/customer/password', headers=headers, json={'password':'my test password','newPassword':'a fresh password'})
        self.assertEqual(good.status_code, 200, good.text)
        self.assertEqual(self.client.get('/forum/me', headers=headers).status_code, 401)
        fresh = {**self.origin, 'authorization':'Bearer '+good.json()['token']}
        self.assertEqual(self.client.get('/customer/me', headers=fresh).status_code, 200)

    def test_owner_can_search_customer_profiles_without_security_secrets(self):
        headers = self.account()
        self.client.post('/customer/me', headers=headers, json={'name':'Alex Private','email':'alex@example.com'})
        self.save_address(headers)
        response = type('Response', (), {'raise_for_status':lambda _:None,'json':lambda _:{'login':'lionsarmor'}})()
        with patch('backend.app.httpx.get', return_value=response):
            r = self.client.get('/admin/customers?search=PRIVATE', headers={'authorization':'Bearer owner-test'})
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(len(r.json()['customers']), 1)
            self.assertEqual(r.json()['customers'][0]['addresses'][0]['address'], ADDRESS)
            self.assertNotIn('password', r.text)
            self.assertNotIn('recovery', r.text)

    def test_existing_community_account_gets_a_customer_profile_on_first_saved_address(self):
        headers = self.account('Existing_Member')
        self.assertEqual(self.save_address(headers).status_code, 200)
        profile = self.client.get('/customer/me', headers=headers).json()
        self.assertEqual(profile['name'], 'Alex Example')
        self.assertEqual(profile['email'], 'alex@example.com')


if __name__ == '__main__':
    unittest.main()
