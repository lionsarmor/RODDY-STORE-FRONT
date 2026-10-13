"""Owner-only supplier discovery, preferences and protected connection storage."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time
from urllib.parse import urlsplit

from fastapi import HTTPException, Request

from .newsletter_mail import text
from .supplier_clients import AliExpress, Mouser, link
from .aliexpress_auth import register_aliexpress_auth

PROVIDERS = {'mouser', 'aliexpress'}


def read_connections(path):
    try:
        data = json.loads(Path(path).read_text())
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        raise HTTPException(503, 'Supplier connection storage needs attention.') from None


def write_connections(path, data):
    path = Path(path)
    temporary = None
    try:
        descriptor, temporary = tempfile.mkstemp(prefix='.suppliers-', dir=path.parent)
        with os.fdopen(descriptor, 'w') as output:
            os.fchmod(output.fileno(), 0o600)
            json.dump(data, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    except OSError:
        raise HTTPException(503, 'Could not save supplier connection. Check the private data directory permissions.') from None
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def register_suppliers(app, connect, require_admin, config_path, public_url, site, rate_limit):
    config_lock = threading.Lock()
    query_lock = threading.Lock()
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS supplier_preferences (
          id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, data TEXT NOT NULL
        );
        INSERT OR IGNORE INTO supplier_preferences VALUES(1,1,'{"favorites":[]}');
        CREATE TABLE IF NOT EXISTS supplier_cache (
          key TEXT PRIMARY KEY, data TEXT NOT NULL, expires INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS supplier_limits (
          bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, expires INTEGER NOT NULL
        );
        """)

    def reserve(provider):
        now = int(time.time())
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM supplier_limits WHERE expires<?', (now,))
            for period, maximum in [(60, 25 if provider == 'mouser' else 15), (86400, 900 if provider == 'mouser' else 500)]:
                bucket = f'{provider}:{period}:{now // period}'
                row = db.execute('SELECT count FROM supplier_limits WHERE bucket=?', (bucket,)).fetchone()
                if row and row[0] >= maximum:
                    raise HTTPException(429, 'Supplier request budget reached. Wait for its minute/day budget to reset. Cached results remain available.')
                db.execute('INSERT INTO supplier_limits VALUES(?,1,?) ON CONFLICT(bucket) DO UPDATE SET count=count+1', (bucket, now + period))

    refresh_buyer, callback_url = register_aliexpress_auth(app, connect, require_admin, config_path,
        read_connections, write_connections, config_lock, reserve, public_url, site, rate_limit)

    def preferences(db):
        row = db.execute('SELECT * FROM supplier_preferences WHERE id=1').fetchone()
        return {**json.loads(row['data']), 'revision': row['revision']}

    def provider_input(value):
        if not isinstance(value, str) or value not in PROVIDERS:
            raise HTTPException(400, 'Choose Mouser or AliExpress.')
        return value

    def connection_status(config):
        return [{'provider': provider,
                 'searchConfigured': bool(config.get(provider, {}).get('searchKey') if provider == 'mouser' else config.get(provider, {}).get('appKey') and config.get(provider, {}).get('appSecret')),
                 'buyerAuthorized': bool(config.get(provider, {}).get('accessToken')) if provider == 'aliexpress' else None,
                 'accessExpiresAt': config.get(provider, {}).get('accessExpiresAt') if provider == 'aliexpress' else None,
                 'refreshAvailable': bool(config.get(provider, {}).get('refreshToken')) if provider == 'aliexpress' else False,
                 'callbackUrl': callback_url if provider == 'aliexpress' else '',
                 'searchVerifiedAt': config.get(provider, {}).get('verifiedAt'),
                 'approvalPending': config.get(provider, {}).get('approvalPending', False),
                 'orderKeyStored': bool(config.get(provider, {}).get('orderKey')) if provider == 'mouser' else False,
                 'orderApprovalPending': config.get(provider, {}).get('orderApprovalPending', False) if provider == 'mouser' else False,
                 'capabilities': {'keywordSearch': True, 'productLookup': True, 'completeSellerCatalog': False, 'orderSubmission': False, 'automaticPayment': False}}
                for provider in sorted(PROVIDERS)]

    def cached(provider, kind, query, page, country):
        with config_lock:
            config = refresh_buyer() if provider == 'aliexpress' else read_connections(config_path).get(provider, {})
        if not config or (provider == 'mouser' and not config.get('searchKey')) or (provider == 'aliexpress' and not (config.get('appKey') and config.get('appSecret'))):
            raise HTTPException(409, 'Connect this supplier in Suppliers settings first. Website browsing is available without API credentials.')
        key_config = {k: v for k, v in config.items() if k not in {'verifiedAt', 'approvalPending'}}
        key = hashlib.sha256(json.dumps([provider, kind, query, page, country, key_config], sort_keys=True).encode()).hexdigest()
        # Bound concurrent API calls and prevent repeated clicks spending the same quota.
        with query_lock:
            now = int(time.time())
            with connect() as db:
                db.execute('DELETE FROM supplier_cache WHERE expires<?', (now,))
                row = db.execute('SELECT data FROM supplier_cache WHERE key=?', (key,)).fetchone()
            if row:
                return {**json.loads(row[0]), 'cached': True}
            client = Mouser(config, reserve) if provider == 'mouser' else AliExpress(config, reserve)
            result = client.search(query, page, country) if kind == 'search' else {'product': client.product(query, country)}
            result.update(checkedAt=now, country=country, provider=provider, page=page)
            with config_lock:
                saved = read_connections(config_path)
                current = saved.get(provider, {})
                if {k: v for k, v in current.items() if k not in {'verifiedAt', 'approvalPending'}} == key_config:
                    current['verifiedAt'] = now
                    current['approvalPending'] = False
                    saved[provider] = current
                    write_connections(config_path, saved)
            with connect() as db:
                db.execute('INSERT OR REPLACE INTO supplier_cache VALUES(?,?,?)', (key, json.dumps(result), now + 300))
            return {**result, 'cached': False}

    @app.get('/admin/suppliers')
    def overview(request: Request):
        require_admin(request)
        with connect() as db:
            return {'connections': connection_status(read_connections(config_path)), 'preferences': preferences(db)}

    @app.post('/admin/suppliers/connections')
    def save_connection(request: Request, body: dict):
        require_admin(request)
        provider = provider_input(body.get('provider'))
        fields = ['searchKey'] if provider == 'mouser' else ['appKey', 'appSecret', 'accessToken']
        with config_lock:
            config = read_connections(config_path)
            entry = dict(config.get(provider, {}))
            if body.get('disconnect') is True:
                if provider == 'mouser' and entry.get('orderKey'):
                    for key in ['searchKey', 'verifiedAt', 'approvalPending']:
                        entry.pop(key, None)
                    config[provider] = entry
                else:
                    config.pop(provider, None)
            else:
                changed_app = provider == 'aliexpress' and any(body.get(k) and body[k] != entry.get(k) for k in ['appKey', 'appSecret'])
                if changed_app or (provider == 'aliexpress' and body.get('accessToken')):
                    for k in ['accessToken', 'refreshToken', 'accessExpiresAt', 'refreshExpiresAt', 'authorizedAt']:
                        entry.pop(k, None)
                for field in fields:
                    if body.get(field):
                        value = text(body[field], 4096 if field == 'accessToken' else 512, 'the API credential', True)
                        if any(c.isspace() for c in value):
                            raise HTTPException(400, 'API credentials cannot contain whitespace.')
                        entry[field] = value
                needed = ['searchKey'] if provider == 'mouser' else ['appKey', 'appSecret']
                if not all(entry.get(field) for field in needed):
                    raise HTTPException(400, 'Complete the required supplier credentials.')
                entry.pop('verifiedAt', None)
                if provider == 'mouser' and isinstance(body.get('approvalPending'), bool):
                    entry['approvalPending'] = body['approvalPending']
                config[provider] = entry
            write_connections(config_path, config)
            if provider == 'aliexpress':
                with connect() as db:
                    db.execute('DELETE FROM supplier_oauth')
        return {'connections': connection_status(config)}

    @app.post('/admin/suppliers/preferences')
    def save_preferences(request: Request, body: dict):
        require_admin(request)
        favorites = body.get('favorites')
        if not isinstance(favorites, list) or len(favorites) > 30:
            raise HTTPException(400, 'Save at most 30 preferred suppliers.')
        clean, ids = [], set()
        for favorite in favorites:
            if not isinstance(favorite, dict):
                raise HTTPException(400, 'Check the preferred supplier.')
            provider = provider_input(favorite.get('provider'))
            identifier = text(favorite.get('id', ''), 64, 'the supplier ID', True)
            if identifier in ids:
                raise HTTPException(400, 'Preferred supplier IDs must be unique.')
            ids.add(identifier)
            store_id = favorite.get('storeId', '')
            if not isinstance(store_id, str) or (store_id and not re.fullmatch(r'\d{1,20}', store_id)):
                raise HTTPException(400, 'AliExpress Store IDs use digits only (up to 20).')
            address = link(favorite.get('url'))
            if provider == 'aliexpress' and store_id and not favorite.get('url'):
                address = 'https://www.aliexpress.com/store/' + store_id
            host = urlsplit(address).hostname or ''
            domains = ['mouser.com'] if provider == 'mouser' else ['aliexpress.com', 'aliexpress.us']
            if not address or not any(host == domain or host.endswith('.' + domain) for domain in domains):
                raise HTTPException(400, 'Use this supplier’s official HTTPS store URL.')
            match = re.search(r'/store/(\d+)', urlsplit(address).path)
            if provider == 'aliexpress' and store_id and match and store_id != match[1]:
                raise HTTPException(400, 'Store ID and store URL refer to different AliExpress stores. Check both fields.')
            if provider == 'aliexpress' and store_id and not match:
                raise HTTPException(400, 'Use an official /store/NUMBER URL matching the Store ID, or leave the URL blank.')
            clean.append({'id': identifier, 'provider': provider, 'name': text(favorite.get('name', ''), 100, 'the supplier name', True),
                          'url': address, 'storeId': match[1] if match else '', 'query': text(favorite.get('query', ''), 160, 'the saved search')})
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if preferences(db)['revision'] != body.get('revision'):
                raise HTTPException(409, 'Supplier preferences changed in another browser. Reload them before saving.')
            db.execute('UPDATE supplier_preferences SET data=?,revision=revision+1 WHERE id=1', (json.dumps({'favorites': clean}),))
            return {'preferences': preferences(db)}

    def query_input(body, maximum=160):
        provider = provider_input(body.get('provider'))
        query = text(body.get('query', ''), maximum, 'a supplier query', True)
        country = body.get('country', 'US')
        page = body.get('page', 1)
        if not isinstance(country, str) or country not in {'US', 'CA'} or type(page) is not int or not 1 <= page <= 1000:
            raise HTTPException(400, 'Choose US/Canada and a valid results page.')
        return provider, query, page, country

    @app.post('/admin/suppliers/search')
    def search(request: Request, body: dict):
        require_admin(request)
        provider, query, page, country = query_input(body)
        return cached(provider, 'search', query, page, country)

    @app.post('/admin/suppliers/product')
    def product(request: Request, body: dict):
        require_admin(request)
        provider, query, page, country = query_input(body, 2000)
        if provider == 'aliexpress' and query.startswith('https://'):
            if not link(query):
                raise HTTPException(400, 'Use a valid HTTPS item URL.')
            parsed = urlsplit(query)
            if not any(parsed.hostname == domain or (parsed.hostname or '').endswith('.' + domain) for domain in ['aliexpress.com', 'aliexpress.us']):
                raise HTTPException(400, 'Use an official AliExpress item URL.')
            match = re.search(r'/item/(\d+)\.html', parsed.path)
            if not match:
                raise HTTPException(400, 'Use an AliExpress /item/NUMBER.html URL or numeric product ID.')
            query = match[1]
        return cached(provider, 'product', query, page, country)
