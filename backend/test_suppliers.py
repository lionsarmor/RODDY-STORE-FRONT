import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.supplier_clients import Mouser, number
from backend.test_checkout import FakeProvider

PART = {'MouserPartNumber': '123-FPGA', 'ManufacturerPartNumber': 'DE10-TEST', 'Manufacturer': 'Test Manufacturer',
        'Description': 'An FPGA development board', 'Availability': '12 In Stock', 'AvailabilityInStock': '12',
        'Min': '1', 'Mult': '1', 'ImagePath': 'https://www.mouser.com/images/test.jpg',
        'ProductDetailUrl': 'https://www.mouser.com/ProductDetail/test', 'PriceBreaks': [
            {'Quantity': 1, 'Price': '$120.01', 'Currency': 'USD'}, {'Quantity': 10, 'Price': '$100.00', 'Currency': 'USD'}]}
ALI_SEARCH = {'code': '0', 'data': {'totalCount': 25, 'products': [{'itemId': '1005001234567', 'title': 'Test MiSTer case',
              'salePrice': '29.95', 'salePriceCurrency': 'USD', 'itemMainPic': 'https://ae01.alicdn.com/test.jpg',
              'itemUrl': 'https://www.aliexpress.com/item/1005001234567.html'}]}}
ALI_PRODUCT = {'result': {'ae_item_base_info_dto': {'subject': 'Test MiSTer case', 'product_id': 1005001234567},
               'ae_store_info': {'store_id': 1234567, 'store_name': 'Test Store'},
               'ae_multimedia_info_dto': {'image_urls': 'https://ae01.alicdn.com/test.jpg'},
               'ae_item_sku_info_dtos': [{'sku_id': 'sku-1', 'sku_price': '29.95', 'currency_code': 'USD', 'sku_available_stock': 4,
                  'ae_sku_property_dtos': [{'sku_property_value': 'Black'}]}]}, 'rsp_code': 200}


class SupplierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / 'store.sqlite3'
        self.client = TestClient(create_app(database=self.database, private_dir=self.root, manifest={}, provider=FakeProvider(),
                                            catalog_loader=lambda: {'products': []}, enabled=False, worker_enabled=False))

    def admin(self, method, path='', body=None, login='lionsarmor'):
        response = type('Response', (), {'raise_for_status': lambda _: None, 'json': lambda _: {'login': login}})()
        with patch('backend.app.httpx.get', return_value=response):
            return self.client.request(method, '/admin/suppliers' + path, json=body, headers={'authorization': 'Bearer test-owner'})

    def connect(self, provider='mouser'):
        body = {'provider': provider, **({'searchKey': 'private-search-key'} if provider == 'mouser' else
                {'appKey': 'test-app-key', 'appSecret': 'private-app-secret', 'accessToken': 'private-buyer-token'})}
        response = self.admin('POST', '/connections', body)
        self.assertEqual(response.status_code, 200, response.text)
        return response

    def test_connection_updates_preserve_private_file_ownership(self):
        from backend.suppliers import write_connections
        path=self.root/'suppliers.json'
        parent=path.parent.stat()
        with patch('backend.suppliers.os.fchown',wraps=__import__('os').fchown) as chown:
            write_connections(path,{'mouser':{'searchKey':'test-only'}})
            self.assertEqual(chown.call_args.args[1:],(parent.st_uid,parent.st_gid))
            previous=path.stat();write_connections(path,{'mouser':{'searchKey':'replacement-test-only'}})
            self.assertEqual(chown.call_args.args[1:],(previous.st_uid,previous.st_gid))
        self.assertEqual(path.stat().st_mode&0o777,0o600)

    def search(self, provider='mouser', query='FPGA', page=1):
        return self.admin('POST', '/search', {'provider': provider, 'query': query, 'page': page, 'country': 'CA'})

    def test_private_access_connections_permissions_and_no_secret_echo(self):
        self.assertEqual(self.client.get('/admin/suppliers').status_code, 401)
        self.assertEqual(self.admin('GET', login='someone-else').status_code, 403)
        self.assertEqual(self.search().status_code, 409)
        response = self.connect()
        self.assertNotIn('private-search-key', response.text)
        self.assertEqual((self.root / 'suppliers.json').stat().st_mode & 0o777, 0o600)
        self.assertNotIn('private-search-key', self.admin('GET').text)
        self.assertFalse(response.json()['connections'][1]['capabilities']['orderSubmission'])
        self.assertEqual(self.admin('POST', '/connections', {'provider': 'mouser'}).status_code, 200)
        self.assertIn('private-search-key', (self.root / 'suppliers.json').read_text())
        self.admin('POST', '/connections', {'provider': 'mouser', 'disconnect': True})
        self.assertNotIn('private-search-key', (self.root / 'suppliers.json').read_text())
        self.assertEqual(self.admin('POST', '/connections', {'provider': {}}).status_code, 400)

    def test_mouser_real_request_schema_prices_paging_and_cache(self):
        self.connect()
        with patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json={'Errors': [], 'SearchResults': {'NumberOfResult': 41, 'Parts': [PART]}})) as post:
            data = self.search(page=2).json()
            self.assertEqual(data['products'][0]['costCents'], 12001)
            self.assertEqual(data['products'][0]['availableQuantity'], 12)
            self.assertTrue(data['hasMore']); self.assertFalse(data['cached'])
            self.assertEqual(post.call_args.args[0], 'https://api.mouser.com/api/v1/search/keyword')
            self.assertEqual(post.call_args.kwargs['json']['SearchByKeywordRequest']['startingRecord'], 20)
            self.assertEqual(post.call_args.kwargs['params']['apiKey'], 'private-search-key')
            self.assertTrue(self.search(page=2).json()['cached'])
            self.assertEqual(post.call_count, 1)
            self.assertNotIn('private-search-key', json.dumps(data))
            self.assertTrue(self.admin('GET').json()['connections'][1]['searchVerifiedAt'])
            with sqlite3.connect(self.database) as db: db.execute('UPDATE supplier_cache SET expires=0')
            self.assertFalse(self.search(page=2).json()['cached']); self.assertEqual(post.call_count, 2)
        part = {**PART, 'AvailabilityInStock': 'unknown', 'PriceBreaks': [{'Quantity': 1, 'Price': '10,00', 'Currency': 'EUR'}]}
        self.assertIsNone(Mouser.part(part)['costCents']); self.assertIsNone(Mouser.part(part)['availableQuantity'])

    def test_mouser_exact_lookup_and_safe_api_failure_messages(self):
        self.connect()
        with patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json={'SearchResults': {'Parts': [PART]}})) as post:
            result = self.admin('POST', '/product', {'provider': 'mouser', 'query': '123-FPGA'})
            self.assertEqual(result.json()['product']['sku'], '123-FPGA')
            self.assertEqual(post.call_args.kwargs['json'], {'SearchByPartRequest': {'mouserPartNumber': '123-FPGA', 'partSearchOptions': 'Exact'}})
        with patch('backend.supplier_clients.httpx.post', side_effect=httpx.ConnectError('private-search-key in exception')):
            response = self.search(query='another query')
            self.assertEqual(response.status_code, 503); self.assertNotIn('private-search-key', response.text)
        with patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json={'Errors': [{'Message': 'private-search-key'}]})):
            response = self.search(query='third query')
            self.assertEqual(response.status_code, 503); self.assertNotIn('private-search-key', response.text)

    def test_shared_durable_daily_api_budget_stops_outbound_requests(self):
        self.assertEqual(number(0), 0)
        self.connect(); now = int(time.time())
        with sqlite3.connect(self.database) as db:
            db.execute('INSERT INTO supplier_limits VALUES(?,900,?)', (f'mouser:86400:{now // 86400}', now + 86400))
        with patch('backend.supplier_clients.httpx.post') as post:
            self.assertEqual(self.search().status_code, 429); post.assert_not_called()

    def test_mouser_invalid_key_explains_account_action_without_echoing_provider_details(self):
        self.connect()
        failure = {'Errors': [{'Code': 'Invalid', 'PropertyName': 'API Key', 'Message': 'Invalid unique identifier: private-search-key'}]}
        with patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json=failure)):
            response = self.search()
        self.assertEqual(response.status_code, 503)
        self.assertIn('invalid unique identifier', response.json()['error'])
        self.assertIn('Search and Order API keys are separate', response.json()['error'])
        self.assertNotIn('private-search-key', response.text)
        status = self.admin('GET').json()['connections'][1]
        self.assertFalse(status['searchVerifiedAt'])

    def test_separate_mouser_order_key_is_private_and_does_not_enable_search(self):
        from backend.suppliers import write_connections
        write_connections(self.root / 'suppliers.json', {'mouser': {'orderKey': 'private-order-key', 'orderApprovalPending': True}})
        overview = self.admin('GET')
        status = overview.json()['connections'][1]
        self.assertTrue(status['orderKeyStored']); self.assertTrue(status['orderApprovalPending'])
        self.assertFalse(status['searchConfigured']); self.assertNotIn('private-order-key', overview.text)
        with patch('backend.supplier_clients.httpx.post') as post:
            self.assertEqual(self.search().status_code, 409); post.assert_not_called()
        self.connect()
        self.assertIn('private-order-key', (self.root / 'suppliers.json').read_text())
        self.admin('POST', '/connections', {'provider': 'mouser', 'disconnect': True})
        saved = json.loads((self.root / 'suppliers.json').read_text())['mouser']
        self.assertNotIn('searchKey', saved); self.assertEqual(saved['orderKey'], 'private-order-key')

    def test_preferred_supplier_official_url_identity_and_revision_conflict(self):
        favorite = {'id': 'retro', 'name': 'Chosen Store', 'provider': 'aliexpress', 'url': 'https://www.aliexpress.com/store/1234567', 'query': 'MiSTer FPGA'}
        result = self.admin('POST', '/preferences', {'revision': 1, 'favorites': [favorite]})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['preferences']['favorites'][0]['storeId'], '1234567')
        self.assertEqual(self.admin('POST', '/preferences', {'revision': 1, 'favorites': []}).status_code, 409)
        for url in ['javascript:alert(1)', 'https://aliexpress.com.evil.test/store/1234567', 'https://example.com']:
            self.assertEqual(self.admin('POST', '/preferences', {'revision': 2, 'favorites': [{**favorite, 'url': url}]}).status_code, 400)
        self.assertEqual(self.admin('GET').json()['preferences']['revision'], 2)
        by_id = {**favorite, 'id': 'retro-by-id', 'url': '', 'storeId': '912024455'}
        result = self.admin('POST', '/preferences', {'revision': 2, 'favorites': [by_id]})
        self.assertEqual(result.status_code, 200, result.text)
        saved = result.json()['preferences']['favorites'][0]
        self.assertEqual(saved['url'], 'https://www.aliexpress.com/store/912024455')
        self.assertEqual(saved['storeId'], '912024455')
        mismatch = {**favorite, 'storeId': '912024455'}
        self.assertEqual(self.admin('POST', '/preferences', {'revision': 3, 'favorites': [mismatch]}).status_code, 400)
        self.assertEqual(self.admin('POST', '/preferences', {'revision': 3, 'favorites': [{**by_id, 'storeId': 'bad-id'}]}).status_code, 400)

    def test_aliexpress_documented_top_search_and_exact_sku_seller_lookup(self):
        self.connect('aliexpress')
        with patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json=ALI_SEARCH)) as post:
            data = self.search('aliexpress', 'MiSTer').json()
            self.assertEqual(data['products'][0]['costCents'], 2995)
            self.assertIsNone(data['products'][0]['availableQuantity'])
            self.assertEqual(post.call_args.args[0], 'https://api-sg.aliexpress.com/sync')
            self.assertEqual(post.call_args.kwargs['data'], {'keyWord': 'MiSTer', 'local': 'en_US', 'countryCode': 'CA', 'currency': 'USD', 'pageSize': '20', 'pageIndex': '1'})
            common = post.call_args.kwargs['params']; self.assertEqual(common['method'], 'aliexpress.ds.text.search')
            self.assertEqual(common['session'], 'private-buyer-token'); self.assertEqual(len(common['sign']), 64)
            self.assertNotIn('private-buyer-token', json.dumps(data))
        with patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json=ALI_PRODUCT)) as post:
            result = self.admin('POST', '/product', {'provider': 'aliexpress', 'query': 'https://www.aliexpress.com/item/1005001234567.html?tracking=' + 'a' * 300})
            self.assertEqual(result.status_code, 200, result.text)
            product = result.json()['product']; self.assertEqual(product['sellerId'], '1234567')
            self.assertEqual(product['variants'][0], {'id': 'sku-1', 'label': 'Black', 'costCents': 2995, 'availableQuantity': 4, 'currency': 'USD'})
            self.assertEqual(post.call_args.kwargs['params']['method'], 'aliexpress.ds.product.get')
        for bad in ['https://example.com/item/1005001234567.html', 'https://[invalid', 'not-an-item']:
            self.assertEqual(self.admin('POST', '/product', {'provider': 'aliexpress', 'query': bad}).status_code, 400)
        with patch('backend.supplier_clients.httpx.post', return_value=httpx.Response(200, json={'error_response': {'msg': 'private-app-secret'}})):
            result = self.search('aliexpress', 'not cached')
            self.assertEqual(result.status_code, 503); self.assertNotIn('private-app-secret', result.text)


if __name__ == '__main__':
    unittest.main()
