"""Read-only supplier adapters. Credentials never leave the server.

Mouser: https://api.mouser.com/api/docs/V1
AliExpress: current Open Service docs and their downloadable Java TOP SDK.
No purchasing/payment API is exposed by these catalog adapters.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timezone
import hashlib
import hmac
import re
import time
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException


def money(value):
    try:
        amount = Decimal(str(value).replace('$', '').replace(',', '').strip())
        if not amount.is_finite() or amount < 0 or amount > 999999:
            return None
        return int((amount * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        return None


def number(value):
    value = str('' if value is None else value).replace(',', '').strip()
    return int(value) if re.fullmatch(r'\d{1,10}', value) else None


def link(value):
    if not isinstance(value, str) or len(value) > 2000:
        return ''
    if value.startswith('//'):
        value = 'https:' + value
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password and not any(c.isspace() for c in value) else ''
    except ValueError:
        return ''


def request(url, **kwargs):
    try:
        response = httpx.post(url, timeout=20, **kwargs)
        if response.status_code == 429:
            raise HTTPException(429, 'Supplier rate limit reached. Wait before searching again.')
        if not response.is_success:
            raise HTTPException(503, 'Supplier rejected the request. Check its API connection, permissions and account dashboard.')
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except (httpx.HTTPError, ValueError):
        # HTTP error strings can contain an API key in a URL; never relay/log them.
        raise HTTPException(503, 'Supplier is unavailable or returned an unreadable response. Try again later.') from None


class Mouser:
    def __init__(self, config, reserve):
        self.key, self.reserve = config['searchKey'], reserve

    @staticmethod
    def part(p):
        minimum = number(p.get('Min')) or 1
        prices = [{'quantity': b.get('Quantity'), 'costCents': money(b.get('Price')), 'currency': b.get('Currency')}
                  for b in p.get('PriceBreaks', []) if isinstance(b, dict)]
        eligible = [b for b in prices if b['currency'] == 'USD' and type(b['quantity']) is int and b['quantity'] <= minimum and b['costCents'] is not None]
        cost = max(eligible, key=lambda b: b['quantity'])['costCents'] if eligible else None
        stock = number(p.get('AvailabilityInStock'))
        return {'provider': 'mouser', 'sku': str(p.get('MouserPartNumber', ''))[:80],
                'name': str(p.get('Description', ''))[:300], 'description': str(p.get('Description', ''))[:5000],
                'manufacturer': str(p.get('Manufacturer', ''))[:160], 'manufacturerPartNumber': str(p.get('ManufacturerPartNumber', ''))[:160],
                'image': link(p.get('ImagePath')), 'url': link(p.get('ProductDetailUrl')), 'datasheet': link(p.get('DataSheetUrl')),
                'costCents': cost, 'currency': 'USD' if cost is not None else None, 'priceBreaks': prices,
                'availableQuantity': stock, 'availability': str(p.get('Availability', 'Unknown'))[:250],
                'minimumQuantity': minimum, 'orderMultiple': number(p.get('Mult')) or 1,
                'leadTime': str(p.get('LeadTime', ''))[:250], 'sellerId': '', 'sellerName': 'Mouser Electronics', 'variants': [],
                'restriction': str(p.get('RestrictionMessage', ''))[:500]}

    def query(self, kind, payload):
        self.reserve('mouser')
        data = request('https://api.mouser.com/api/v1/search/' + kind, params={'apiKey': self.key}, json=payload)
        if data.get('Errors'):
            if any(isinstance(e, dict) and str(e.get('Code', '')).lower() == 'invalid'
                   and str(e.get('PropertyName', '')).lower().replace(' ', '') == 'apikey'
                   for e in data['Errors']):
                raise HTTPException(503, 'Mouser rejected the saved Search API key (invalid unique identifier). In My Mouser → API access, check Search API approval and copy the active Search API key into Supplier connections. Search and Order API keys are separate.')
            raise HTTPException(503, 'Mouser could not complete the search. Check the Search API key, account and remaining quota.')
        result = data.get('SearchResults')
        if not isinstance(result, dict) or not isinstance(result.get('Parts', []), list):
            raise HTTPException(503, 'Mouser returned an unexpected search response.')
        return result

    def search(self, query, page, country):
        result = self.query('keyword', {'SearchByKeywordRequest': {'keyword': query, 'records': 20, 'startingRecord': (page - 1) * 20, 'searchOptions': 'None', 'searchWithYourSignUpLanguage': 'false'}})
        total = number(result.get('NumberOfResult'))
        return {'products': [self.part(p) for p in result.get('Parts', []) if isinstance(p, dict)], 'total': total,
                'hasMore': total is not None and page * 20 < total}

    def product(self, sku, country):
        if not re.fullmatch(r'[^\s|]{3,40}', sku):
            raise HTTPException(400, 'Enter one Mouser part number (3–40 characters).')
        parts = self.query('partnumber', {'SearchByPartRequest': {'mouserPartNumber': sku, 'partSearchOptions': 'Exact'}}).get('Parts', [])
        found = next((p for p in parts if p.get('MouserPartNumber', '').lower() == sku.lower()), None)
        if not found and len(parts) == 1:
            found = parts[0]
        if not found:
            raise HTTPException(404, 'Mouser part not found. Choose its exact Mouser part number from search.')
        return self.part(found)


class AliExpress:
    def __init__(self, config, reserve):
        self.config, self.reserve = config, reserve

    def call(self, method, params, require_token=False):
        if require_token and not self.config.get('accessToken'):
            raise HTTPException(409, 'AliExpress product details need an authorized buyer access token. Complete its protected connection setup.')
        self.reserve('aliexpress')
        common = {'app_key': self.config['appKey'], 'timestamp': str(int(time.time() * 1000)), 'sign_method': 'sha256', 'method': method, 'v': '2.0', 'format': 'json', 'simplify': 'true'}
        if self.config.get('accessToken'):
            common['session'] = self.config['accessToken']
        combined = {**params, **common}
        canonical = ''.join(k + str(combined[k]) for k in sorted(combined) if str(combined[k]))
        common['sign'] = hmac.new(self.config['appSecret'].encode(), canonical.encode(), hashlib.sha256).hexdigest().upper()
        data = request('https://api-sg.aliexpress.com/sync', params=common, data=params)
        if data.get('error_response') or data.get('type') in {'ISP', 'ISV', 'SYSTEM', 'ISV_ERROR'}:
            raise HTTPException(503, 'AliExpress rejected API access. Check application permissions, authorization and token expiry in its developer console.')
        return data

    def search(self, query, page, country):
        data = self.call('aliexpress.ds.text.search', {'keyWord': query, 'local': 'en_US', 'countryCode': country, 'currency': 'USD', 'pageSize': '20', 'pageIndex': str(page)})
        data = data.get('aliexpress_ds_text_search_response', data)
        if data.get('code') not in {None, 0, '0', '00'}:
            raise HTTPException(503, 'AliExpress search failed. Check application permissions and account access.')
        result = data.get('data')
        if not isinstance(result, dict):
            raise HTTPException(503, 'AliExpress search is not available for this application. Check its Dropship API permission.')
        products = result.get('products', [])
        if isinstance(products, dict):
            products = products.get('selection_search_product', [])
        if not isinstance(products, list):
            raise HTTPException(503, 'AliExpress returned an unexpected product list.')
        rows = []
        for p in products:
            currency = p.get('targetSalePriceCurrency') or p.get('salePriceCurrency')
            rows.append({'provider': 'aliexpress', 'sku': str(p.get('itemId', ''))[:80], 'name': str(p.get('title', ''))[:300],
                         'description': '', 'manufacturer': '', 'manufacturerPartNumber': '', 'image': link(p.get('itemMainPic')),
                         'url': link(p.get('itemUrl')), 'datasheet': '', 'costCents': money(p.get('targetSalePrice') or p.get('salePrice')) if currency == 'USD' else None,
                         'currency': currency, 'availableQuantity': None, 'availability': 'Select a SKU and check current stock',
                         'minimumQuantity': 1, 'orderMultiple': 1, 'leadTime': '', 'sellerId': '', 'sellerName': '', 'variants': [], 'priceBreaks': [], 'restriction': ''})
        total = number(result.get('totalCount'))
        return {'products': rows, 'total': total, 'hasMore': total is not None and page * 20 < total}

    def product(self, sku, country):
        if not re.fullmatch(r'\d{5,30}', sku):
            raise HTTPException(400, 'Enter an AliExpress numeric product ID or its item URL.')
        data = self.call('aliexpress.ds.product.get', {'ship_to_country': country, 'product_id': sku, 'target_currency': 'USD', 'target_language': 'EN', 'remove_personal_benefit': 'true'}, True)
        data = data.get('aliexpress_ds_product_get_response', data)
        if data.get('rsp_code') not in {None, 200, '200'}:
            raise HTTPException(503, 'AliExpress product lookup failed. Check buyer authorization and item availability.')
        result = data.get('result')
        if not isinstance(result, dict):
            raise HTTPException(503, 'AliExpress product details are unavailable. Check buyer authorization and product availability.')
        base, store = result.get('ae_item_base_info_dto', {}), result.get('ae_store_info', {})
        variants = result.get('ae_item_sku_info_dtos', [])
        if isinstance(variants, dict):
            variants = variants.get('ae_item_sku_info_d_t_o', [])
        options = []
        for v in variants:
            attributes = v.get('ae_sku_property_dtos', [])
            if isinstance(attributes, dict):
                attributes = attributes.get('ae_sku_property_d_t_o', [])
            options.append({'id': str(v.get('sku_id', ''))[:100], 'label': ' / '.join(str(a.get('property_value_definition_name') or a.get('sku_property_value', '')) for a in attributes)[:250],
                            'costCents': money(v.get('offer_sale_price') or v.get('sku_price')) if v.get('currency_code') == 'USD' else None,
                            'availableQuantity': number(v.get('sku_available_stock')), 'currency': v.get('currency_code')})
        images = [link(image) for image in str(result.get('ae_multimedia_info_dto', {}).get('image_urls', '')).split(';')]
        return {'provider': 'aliexpress', 'sku': sku, 'name': str(base.get('subject', ''))[:300], 'description': '', 'manufacturer': '',
                'manufacturerPartNumber': '', 'url': 'https://www.aliexpress.com/item/' + sku + '.html', 'image': next((image for image in images if image), ''),
                'datasheet': '', 'variants': options, 'costCents': None, 'currency': 'USD', 'availableQuantity': None,
                'availability': 'Choose a variant to see stock and price', 'minimumQuantity': 1, 'orderMultiple': 1,
                'sellerId': str(store.get('store_id', ''))[:50], 'sellerName': str(store.get('store_name', ''))[:160],
                'leadTime': str(result.get('logistics_info_dto', {}).get('delivery_time', ''))[:100], 'priceBreaks': [], 'restriction': ''}


class MouserOrdering:
    """Read-only account readiness; order submission is a separate capability."""
    def __init__(self, config, reserve):
        self.key,self.reserve=config.get('orderKey'),reserve

    def options(self):
        if not self.key:
            raise HTTPException(409,'Save the separate Mouser Order/Cart API key first.')
        self.reserve('mouser')
        try:
            response=httpx.post('https://api.mouser.com/api/v1/order/options/query',
                params={'apiKey':self.key},json={'OrderInitialize':{'CurrencyCode':'USD'}},timeout=20)
            if response.status_code in {401,403}:
                raise HTTPException(409,'Mouser rejected the Order/Cart API connection. Check its approval and save the active Order/Cart key; the Search key is different.')
            if not response.is_success:raise HTTPException(503,'Mouser ordering options are unavailable. No order was placed.')
            result=response.json()
            if not isinstance(result,dict) or not isinstance(result.get('OrderInitialize'),dict):
                raise HTTPException(503,'Mouser returned incomplete account options. No order was placed.')
            result=result['OrderInitialize']
            if result.get('Errors'):raise HTTPException(409,'Mouser account options need attention. Check billing and Order/Cart API access in My Mouser.')
            payment=result.get('Payment');shipping=result.get('Shipping')
            billing=result.get('BillingAddress') or {}
            if (not isinstance(payment,dict) or not isinstance(shipping,dict) or not isinstance(billing,dict)
                    or not isinstance(result.get('CurrencyCode'),str)
                    or not isinstance(payment.get('PaymentTypes'),list) or not isinstance(shipping.get('Methods'),list)
                    or any(not isinstance(card,dict) for card in payment['PaymentTypes'])):
                raise HTTPException(503,'Mouser returned incomplete account options. No order was placed.')
            # The API exposes expiry only in its display name, not a structured
            # field. Unknown formats must stay unknown, never imply a valid card.
            cards=[card for card in payment.get('PaymentTypes') or [] if card.get('CreditCardLastFourDigits')]
            current=datetime.now(timezone.utc)
            expired=unexpired=0
            for card in cards:
                match=re.search(r'\bExp\s+(0?[1-9]|1[0-2])/(\d{4}|\d{2})\b',str(card.get('Name','')),re.IGNORECASE)
                if match:
                    month,year=map(int,match.groups())
                    if year<100:year+=2000
                    if (year,month)<(current.year,current.month):expired+=1
                    else:unexpired+=1
            unknown=len(cards)-expired-unexpired
            if not cards:
                status='missing';message='No saved card returned by Mouser. Add a card in My Mouser before setting up automatic payment.'
            elif unexpired:
                status='on-file';message='An unexpired saved card is on file. Payment has not been tested; automatic purchasing is not enabled.'
            elif unknown:
                status='unverified';message='Mouser returned a saved card without a recognized expiry. Check it in My Mouser before setting up automatic payment.'
            else:
                status='expired';message='All saved cards returned by Mouser are expired. Update the saved card in My Mouser before setting up automatic payment.'
            return {'accessVerified':True,'billingReady':bool(billing) and not bool(billing.get('Error')),
                    'currency':result.get('CurrencyCode'),'shippingMethods':len(shipping.get('Methods') or []),
                    'paymentMethods':len(payment.get('PaymentTypes') or []),'savedCards':len(cards),
                    'expiredCards':expired,'unexpiredCards':unexpired,'unknownExpiryCards':unknown,
                    'cardStatus':status,'message':message,'paymentVerified':False,'orderPlaced':False}
        except (httpx.HTTPError,ValueError):
            raise HTTPException(503,'Mouser ordering connection could not be checked. No order was placed.') from None
