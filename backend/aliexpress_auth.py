"""Owner-started, browser-bound AliExpress buyer authorization; no public tokens."""
import hashlib
from html import escape
import hmac
import re
import secrets
import time
from urllib.parse import urlencode, urlsplit

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .supplier_clients import request as supplier_request

COOKIE = '__Host-roddy-aliexpress'
CALLBACK = '/suppliers/aliexpress/callback'


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def identity(config):
    return digest(config.get('appKey', '') + '\0' + config.get('appSecret', ''))


def token_request(config, field, value):
    path = '/auth/token/create' if field == 'code' else '/auth/token/refresh'
    params = {'app_key': config['appKey'], 'timestamp': str(int(time.time() * 1000)),
              'sign_method': 'sha256', field: value}
    # GOP signs the API path followed by sorted parameters (official Java SDK).
    canonical = path + ''.join(k + params[k] for k in sorted(params))
    params['sign'] = hmac.new(config['appSecret'].encode(), canonical.encode(), hashlib.sha256).hexdigest().upper()
    data = supplier_request('https://api-sg.aliexpress.com/rest' + path, data=params)
    token = data.get('access_token')
    if str(data.get('code')) != '0' or not isinstance(token, str) or not token or len(token) > 4096 or any(c.isspace() for c in token):
        raise HTTPException(503, 'AliExpress could not authorize this buyer. Check application permissions and authorize again.')
    now = int(time.time())
    def expiry(name):
        value = data.get(name)
        if isinstance(value, bool) or not re.fullmatch(r'\d{1,8}', str(value)) or not 0 <= int(value) <= 366 * 86400:
            raise HTTPException(503, 'AliExpress returned an invalid token lifetime. Authorize again.')
        return now + int(value)
    access_expiry, refresh_expiry = expiry('expires_in'), expiry('refresh_expires_in')
    if access_expiry <= now:
        raise HTTPException(503, 'AliExpress returned an expired buyer token. Authorize again.')
    refresh = data.get('refresh_token', '')
    if not isinstance(refresh, str) or len(refresh) > 4096 or any(c.isspace() for c in refresh):
        raise HTTPException(503, 'AliExpress returned invalid authorization data. Authorize again.')
    return {'accessToken': token, 'accessExpiresAt': access_expiry,
            'refreshToken': refresh if refresh_expiry > now else '', 'refreshExpiresAt': refresh_expiry,
            'authorizedAt': now}


def register_aliexpress_auth(app, connect, require_admin, config_path, read, write, lock, reserve, public_url, site, rate_limit):
    parsed = urlsplit(public_url)
    configured = parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username and not parsed.password and parsed.path in {'', '/'} and not parsed.query and not parsed.fragment
    callback = public_url.rstrip('/') + CALLBACK if configured else ''
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS supplier_oauth (token TEXT PRIMARY KEY, stage TEXT NOT NULL, config TEXT NOT NULL, browser TEXT NOT NULL, expires INTEGER NOT NULL)')

    def entry():
        result = read(config_path).get('aliexpress', {})
        if not result.get('appKey') or not result.get('appSecret'):
            raise HTTPException(409, 'Save the AliExpress App Key and App Secret first.')
        return result

    def ticket(stage, config, browser=''):
        value = secrets.token_urlsafe(32)
        with connect() as db:
            db.execute('DELETE FROM supplier_oauth WHERE expires<?', (int(time.time()),))
            db.execute('INSERT INTO supplier_oauth VALUES(?,?,?,?,?)', (digest(value), stage, identity(config), browser, int(time.time()) + 600))
        return value

    def consume(value, stage, config, browser=''):
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', value):
            raise HTTPException(400, 'Authorization expired or invalid. Start again from Suppliers admin.')
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM supplier_oauth WHERE token=?', (digest(value),)).fetchone()
            if not row or row['stage'] != stage or row['expires'] <= time.time() or row['config'] != identity(config) or not hmac.compare_digest(row['browser'], browser):
                raise HTTPException(400, 'Authorization expired or invalid. Start again from Suppliers admin.')
            db.execute('DELETE FROM supplier_oauth WHERE token=?', (digest(value),))

    def refresh(force=False):
        # Checkout, admin and maintenance all share the same rotation lock.
        with lock:
            return refresh_locked(force)

    def refresh_locked(force=False):
        config = read(config_path)
        current = dict(config.get('aliexpress', {}))
        now = time.time()
        access_due = bool(current.get('accessExpiresAt') and current['accessExpiresAt'] <= now + 1800)
        refresh_due = bool(current.get('refreshToken') and now < current.get('refreshExpiresAt', 0) <= now + 1800)
        # Some grants have a shorter refresh lifetime than access lifetime.
        # Renew before either deadline, while the refresh token still works.
        if not force and not access_due and not refresh_due:
            return current
        if not current.get('refreshToken') or current.get('refreshExpiresAt', 0) <= now:
            raise HTTPException(409, 'AliExpress buyer authorization needs renewal. Use Authorize AliExpress buyer in Suppliers admin.')
        reserve('aliexpress')
        current.update(token_request(current, 'refresh_token', current['refreshToken']))
        current.pop('verifiedAt', None)
        config['aliexpress'] = current
        write(config_path, config)
        return current

    @app.post('/admin/suppliers/aliexpress/authorize')
    def start(request: Request, body: dict):
        require_admin(request)
        if not callback:
            raise HTTPException(503, 'Configure the backend HTTPS public URL before buyer authorization.')
        with lock:
            value = ticket('start', entry())
        return {'url': public_url.rstrip('/') + '/suppliers/aliexpress/authorize?' + urlencode({'ticket': value}), 'callbackUrl': callback}

    @app.get('/suppliers/aliexpress/authorize')
    def authorize(request: Request):
        rate_limit(request, 'supplier-oauth', 20)
        with lock:
            config = entry()
            consume(request.query_params.get('ticket', ''), 'start', config)
            browser = secrets.token_urlsafe(32)
            state = ticket('callback', config, digest(browser))
        response = RedirectResponse('https://api-sg.aliexpress.com/oauth/authorize?' + urlencode({
            'response_type': 'code', 'force_auth': 'true', 'redirect_uri': callback,
            'client_id': config['appKey'], 'state': state}), status_code=303)
        # Set on a top-level backend visit, avoiding third-party cookie restrictions.
        response.set_cookie(COOKIE, browser, max_age=600, secure=True, httponly=True, samesite='lax', path='/')
        return response

    @app.get(CALLBACK)
    def complete(request: Request):
        rate_limit(request, 'supplier-oauth', 20)
        with lock:
            config = read(config_path)
            current = entry()
            browser = request.cookies.get(COOKIE, '')
            consume(request.query_params.get('state', ''), 'callback', current, digest(browser) if browser else '')
            code = request.query_params.get('code', '')
            if request.query_params.get('error') or not code or len(code) > 4096 or any(c.isspace() for c in code):
                raise HTTPException(400, 'AliExpress authorization was not completed. Start again from Suppliers admin.')
            reserve('aliexpress')
            current.update(token_request(current, 'code', code))
            current.pop('verifiedAt', None)
            config['aliexpress'] = current
            write(config_path, config)
        response = HTMLResponse('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>AliExpress connected</title><h1>AliExpress buyer connected</h1><p>Your authorization is saved privately on the RODDY server. Return to Suppliers admin, reload settings, and run a search and exact product lookup to verify permissions. This does not enable supplier purchases.</p><a href="' + escape(site, quote=True) + '/admin.html">Return to RODDY admin</a></html>')
        response.headers['Content-Security-Policy'] = "default-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        response.delete_cookie(COOKIE, secure=True, httponly=True, samesite='lax', path='/')
        return response

    @app.post('/admin/suppliers/aliexpress/refresh')
    def renew(request: Request, body: dict):
        require_admin(request)
        with lock:
            entry()
            refresh(True)
        return {'saved': True}

    return refresh, callback
