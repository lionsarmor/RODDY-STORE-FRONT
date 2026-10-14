import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi.testclient import TestClient
from fastapi import HTTPException

from backend.aliexpress_auth import CALLBACK, COOKIE
from backend.app import create_app
from backend.test_checkout import FakeProvider

TOKENS = {'code': '0', 'access_token': 'private-access', 'refresh_token': 'private-refresh',
          'expires_in': 3600, 'refresh_expires_in': 7200, 'account': 'private-account'}


class AliExpressAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.database = self.root / 'store.sqlite3'
        self.config = self.root / 'suppliers.json'
        self.app = create_app(database=self.database, private_dir=self.root, manifest={}, provider=FakeProvider(),
            catalog_loader=lambda: {'products': []}, enabled=False, worker_enabled=False,
            public_url='https://store-api.example', site='https://roddy.world')
        self.client = TestClient(self.app, base_url='https://store-api.example')
        self.addCleanup(self.client.close)
        self.owner = patch('backend.app.httpx.get', return_value=httpx.Response(200, json={'login': 'lionsarmor'}, request=httpx.Request('GET', 'https://api.github.com/user')))
        self.owner.start(); self.addCleanup(self.owner.stop)
        self.admin('/connections', {'provider': 'mouser', 'searchKey': 'keep-mouser'})
        self.admin('/connections', {'provider': 'aliexpress', 'appKey': 'app-123', 'appSecret': 'private-secret'})

    def admin(self, path, body=None):
        return self.client.request('GET' if body is None else 'POST', '/admin/suppliers'+path,
            json=body, headers={'Authorization': 'Bearer owner-token'})

    def start(self):
        result = self.admin('/aliexpress/authorize', {}).json()
        self.assertEqual(result['callbackUrl'], 'https://store-api.example'+CALLBACK)
        response = self.client.get(result['url'], follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        params = parse_qs(urlsplit(response.headers['location']).query)
        self.assertEqual(params['client_id'], ['app-123'])
        self.assertEqual(params['redirect_uri'], ['https://store-api.example'+CALLBACK])
        self.assertIn('Secure', response.headers['set-cookie']); self.assertIn('HttpOnly', response.headers['set-cookie'])
        self.assertIn('SameSite=lax', response.headers['set-cookie'])
        return params['state'][0], result['url']

    def complete(self, state, code='authorization-code'):
        return self.client.get(CALLBACK, params={'state': state, 'code': code}, follow_redirects=False)

    def test_owner_only_start_one_use_and_browser_bound_callback(self):
        self.assertEqual(self.client.post('/admin/suppliers/aliexpress/authorize', json={}).status_code, 401)
        state, start_url = self.start()
        self.assertEqual(self.client.get(start_url, follow_redirects=False).status_code, 400)
        with sqlite3.connect(self.database) as db:
            saved = db.execute('SELECT token,browser FROM supplier_oauth').fetchone()
        self.assertEqual(saved[0], hashlib.sha256(state.encode()).hexdigest())
        self.assertNotIn(state, saved)
        browser = self.client.cookies.get(COOKIE)
        self.client.cookies.clear()
        with patch('backend.supplier_clients.httpx.post') as post:
            self.assertEqual(self.complete(state).status_code, 400); post.assert_not_called()
        self.client.cookies.set(COOKIE, browser, domain='store-api.example', path='/')
        with patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json=TOKENS)):
            self.assertEqual(self.complete(state).status_code, 200)
            self.assertEqual(self.complete(state).status_code, 400)

    def test_gop_exchange_private_storage_status_and_other_supplier_preserved(self):
        state, _ = self.start()
        with patch('backend.aliexpress_auth.time.time', return_value=1791850000), patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json=TOKENS)) as post:
            response = self.complete(state)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(post.call_args.args[0], 'https://api-sg.aliexpress.com/rest/auth/token/create')
        params = post.call_args.kwargs['data']
        self.assertEqual(params['code'], 'authorization-code')
        self.assertNotIn('params', post.call_args.kwargs)
        self.assertEqual(params['sign'], '26DD7F866F2F828D20904783387EB7CC676DEDAA1D674B08A65879A701BDC458')
        self.assertNotIn('private-secret', str(params))
        saved = json.loads(self.config.read_text())
        self.assertEqual(saved['mouser']['searchKey'], 'keep-mouser')
        self.assertEqual(saved['aliexpress']['accessToken'], 'private-access')
        self.assertEqual(saved['aliexpress']['refreshToken'], 'private-refresh')
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        status = self.admin('').text
        for private in ['private-access', 'private-refresh', 'private-secret', 'private-account', 'authorization-code']:
            self.assertNotIn(private, response.text+status)
        self.assertEqual(response.headers['referrer-policy'], 'no-referrer')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        with patch('backend.suppliers.time.time', return_value=1791850001):
            connection = next(c for c in self.admin('').json()['connections'] if c['provider']=='aliexpress')
        self.assertTrue(connection['buyerAuthorized']); self.assertTrue(connection['refreshAvailable'])
        self.assertEqual(connection['accessExpiresAt'], 1791853600)
        self.assertEqual(connection['refreshExpiresAt'], 1791857200)

    def test_expired_state_changed_application_and_disconnect_invalidate_flow(self):
        state, _ = self.start()
        with sqlite3.connect(self.database) as db: db.execute('UPDATE supplier_oauth SET expires=0')
        with patch('backend.supplier_clients.httpx.post') as post:
            self.assertEqual(self.complete(state).status_code, 400); post.assert_not_called()
        state, _ = self.start()
        self.admin('/connections', {'provider': 'aliexpress', 'appSecret': 'replacement-secret'})
        self.assertEqual(self.complete(state).status_code, 400)
        state, _ = self.start()
        self.admin('/connections', {'provider': 'aliexpress', 'disconnect': True})
        self.assertEqual(self.complete(state).status_code, 409)

    def test_failed_exchange_and_denied_authorization_keep_existing_connection(self):
        for result in [{'code': 'InvalidCode', 'message': 'private-access'}, {**TOKENS, 'expires_in': -1}, {**TOKENS, 'access_token': ''}]:
            state, _ = self.start()
            before = self.config.read_text()
            with patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json=result)):
                response = self.complete(state)
            self.assertEqual(response.status_code, 503)
            self.assertNotIn('private-access', response.text); self.assertEqual(before, self.config.read_text())
            self.assertEqual(self.complete(state).status_code, 400)
        state, _ = self.start()
        with patch('backend.supplier_clients.httpx.post') as post:
            self.assertEqual(self.client.get(CALLBACK, params={'state': state, 'error': 'access_denied'}).status_code, 400)
            post.assert_not_called()

    def test_refresh_rotation_before_read_and_manual_credentials_reset(self):
        state, _ = self.start()
        with patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json=TOKENS)):
            self.complete(state)
        saved = json.loads(self.config.read_text()); saved['aliexpress']['accessExpiresAt'] = int(time.time())+10
        self.config.write_text(json.dumps(saved))
        search = {'code': '0', 'data': {'totalCount': 0, 'products': []}}
        with patch('backend.supplier_clients.httpx.post', side_effect=[httpx.Response(200, json={**TOKENS, 'access_token': 'rotated-access', 'refresh_token': 'rotated-refresh'}), httpx.Response(200, json=search)]) as post:
            response = self.admin('/search', {'provider': 'aliexpress', 'query': 'case'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(post.call_args_list[0].args[0], 'https://api-sg.aliexpress.com/rest/auth/token/refresh')
        self.assertEqual(post.call_args_list[1].kwargs['params']['session'], 'rotated-access')
        self.assertEqual(json.loads(self.config.read_text())['aliexpress']['refreshToken'], 'rotated-refresh')
        self.admin('/connections', {'provider': 'aliexpress', 'accessToken': 'manual-token'})
        self.assertNotIn('refreshToken', json.loads(self.config.read_text())['aliexpress'])
        self.assertEqual(self.admin('/aliexpress/refresh', {}).status_code, 409)
        self.admin('/connections', {'provider': 'aliexpress', 'appKey': 'new-app'})
        self.assertNotIn('accessToken', json.loads(self.config.read_text())['aliexpress'])

    def test_failed_refresh_preserves_saved_tokens_and_expired_renewal_requests_login(self):
        state, _ = self.start()
        with patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json=TOKENS)):
            self.complete(state)
        before = self.config.read_text()
        with patch('backend.supplier_clients.httpx.post', side_effect=httpx.ConnectError('private-refresh in exception')):
            response = self.admin('/aliexpress/refresh', {})
        self.assertEqual(response.status_code, 503); self.assertNotIn('private-refresh', response.text)
        self.assertEqual(before, self.config.read_text())
        data = json.loads(before); data['aliexpress']['refreshExpiresAt'] = 0
        self.config.write_text(json.dumps(data))
        self.assertEqual(self.admin('/aliexpress/refresh', {}).status_code, 409)
        connection = next(c for c in self.admin('').json()['connections'] if c['provider']=='aliexpress')
        self.assertFalse(connection['refreshAvailable'])

    def test_checkout_renews_when_refresh_token_expires_before_access_token(self):
        state, _ = self.start()
        with patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json=TOKENS)):
            self.complete(state)
        saved = json.loads(self.config.read_text())
        saved['aliexpress'].update(accessExpiresAt=int(time.time())+86400, refreshExpiresAt=int(time.time())+600)
        self.config.write_text(json.dumps(saved))
        with patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json={**TOKENS, 'access_token': 'renewed-before-refresh-expiry'})) as post:
            adapter = self.app.state.commerce.supplier_quote_factory('aliexpress')
        self.assertEqual(adapter.client.config['accessToken'], 'renewed-before-refresh-expiry')
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.args[0], 'https://api-sg.aliexpress.com/rest/auth/token/refresh')
        self.assertEqual(json.loads(self.config.read_text())['mouser']['searchKey'], 'keep-mouser')


class QuietStoreRenewalTests(unittest.TestCase):
    def setUp(self):
        from contextlib import contextmanager
        from fastapi import FastAPI
        from backend.suppliers import register_suppliers
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root/'suppliers.json'
        self.config.write_text(json.dumps({'aliexpress': {
            'appKey': 'test', 'appSecret': 'test', 'accessToken': 'old-access', 'refreshToken': 'old-refresh',
            'accessExpiresAt': int(time.time())+86400, 'refreshExpiresAt': int(time.time())+600}}))
        @contextmanager
        def connect():
            db = sqlite3.connect(self.root/'test.sqlite3'); db.row_factory = sqlite3.Row
            try:
                with db: yield db
            finally: db.close()
        self.services = register_suppliers(FastAPI(), connect, lambda _:None, self.config, 'https://api.example.test', 'https://roddy.world', lambda *_:None)

    def test_maintenance_renews_without_checkout_and_throttles_failed_retries(self):
        with patch('backend.suppliers.time.monotonic', return_value=1000), patch('backend.supplier_clients.httpx.post', side_effect=httpx.ConnectError('unavailable')) as post:
            with self.assertRaises(HTTPException): self.services['maintain']()
            self.services['maintain']()
            self.assertEqual(post.call_count, 1)
        self.assertEqual(json.loads(self.config.read_text())['aliexpress']['accessToken'], 'old-access')
        with patch('backend.suppliers.time.monotonic', return_value=1301), patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json=TOKENS)) as post:
            self.services['maintain']()
            self.assertEqual(post.call_count, 1)
        self.assertEqual(json.loads(self.config.read_text())['aliexpress']['accessToken'], TOKENS['access_token'])

    def test_maintenance_never_reauthorizes_disconnected_or_expired_grants(self):
        for index, config in enumerate([{}, {'accessToken':'old', 'refreshToken':'old', 'refreshExpiresAt':0}]):
            self.config.write_text(json.dumps({'aliexpress':config}))
            with patch('backend.suppliers.time.monotonic', return_value=2000+index*1000), patch('backend.supplier_clients.httpx.post') as post:
                self.services['maintain']()
                post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
