"""Private, versioned project documents; owner-issued links expire after two hours."""
import hashlib
import html
import json
import mimetypes
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

LINK_SECONDS = 7200
HEADERS = {"Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer",
           "X-Content-Type-Options": "nosniff", "X-Robots-Tag": "noindex, nofollow",
           "Content-Security-Policy": "sandbox allow-scripts allow-downloads allow-popups allow-popups-to-escape-sandbox; default-src 'self' data:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"}


def register_project_workshop(app, require_admin, directory):
    root = Path(directory)

    def manifest():
        try:
            return json.loads((root / 'library/manifest.json').read_text())
        except FileNotFoundError:
            raise HTTPException(503, 'Project documents have not been uploaded yet.')

    @contextmanager
    def connect():
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        db = sqlite3.connect(root / 'sessions.sqlite3')
        try:
            db.execute('CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY, expires INTEGER)')
            with db:
                yield db
        finally:
            db.close()

    @app.get('/admin/workshop')
    def listing(request: Request):
        require_admin(request)
        data = manifest()
        return JSONResponse({k: data[k] for k in ('updatedAt', 'entries', 'projects')}, headers={'Cache-Control': 'private, no-store'})

    @app.post('/admin/workshop/open')
    async def open_document(request: Request):
        require_admin(request)
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(400, 'Choose a project document.')
        data = manifest()
        entry = next((e for e in data['entries'] if isinstance(body, dict) and e['id'] == body.get('id')), None)
        if not entry:
            raise HTTPException(404, 'Project document not found.')
        token = secrets.token_urlsafe(32)
        expires = int(time.time()) + LINK_SECONDS
        with connect() as db:
            db.execute('DELETE FROM sessions WHERE expires<=?', (int(time.time()),))
            db.execute('INSERT INTO sessions VALUES (?,?)', (hashlib.sha256(token.encode()).hexdigest(), expires))
        return JSONResponse({'path': '/workshop/view/' + token + '/' + quote(entry['path']), 'expiresAt': expires}, headers={'Cache-Control': 'private, no-store'})

    @app.get('/workshop/view/{token}/{path:path}')
    def view_document(token: str, path: str, request: Request):
        if len(token) != 43:
            raise HTTPException(404, 'Document not found.')
        with connect() as db:
            valid = db.execute('SELECT 1 FROM sessions WHERE digest=? AND expires>?',
                               (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
        if not valid:
            return HTMLResponse('<h1>This project link has expired.</h1><p>Return to Project Workshop in the RODDY admin panel and open it again.</p>', status_code=410, headers=HEADERS)
        data = manifest()
        if '\\' in path or any(p in ('.', '..') or p.startswith('.') for p in path.split('/') if p):
            raise HTTPException(404, 'Document not found.')
        base = (root / 'library').resolve()
        target = (base / path).resolve()
        if not target.is_relative_to(base):
            raise HTTPException(404, 'Document not found.')
        files = data['files']
        if path in files and target.is_file():
            mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
            if target.suffix.lower() in {'.md', '.csv', '.txt', '.pos'}:
                mime = 'text/plain'
            encoded = files[path].get('gzip')
            if encoded and encoded in files and 'gzip' in [p.strip().lower() for p in request.headers.get('accept-encoding', '').split(',')]:
                compressed = (base / encoded).resolve()
                if compressed.is_relative_to(base) and compressed.is_file():
                    return FileResponse(compressed, media_type=mime, headers={**HEADERS, 'Content-Encoding':'gzip', 'Vary':'Accept-Encoding'})
            return FileResponse(target, media_type=mime, headers={**HEADERS, 'Vary':'Accept-Encoding'})
        prefix = path.rstrip('/') + '/' if path else ''
        children = sorted({p[len(prefix):].split('/')[0] for p in files if p.startswith(prefix) and p != path})
        if not children:
            raise HTTPException(404, 'Document not found.')
        if path and not path.endswith('/'):
            return RedirectResponse(request.url.path + '/', headers=HEADERS)
        for index in ('OPEN_ME.html', 'index.html'):
            if prefix + index in files:
                return RedirectResponse(quote(index), headers=HEADERS)
        links = []
        for name in children:
            directory = prefix + name not in files
            value = name + ('/' if directory else '')
            links.append(f'<li><a href="{quote(value)}">{html.escape(value)}</a></li>')
        return HTMLResponse('<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>RODDY project files</title><style>body{font:17px/1.7 system-ui;background:#f4eee3;color:#231f20;max-width:1000px;margin:40px auto;padding:20px}a{color:#ae2925}li{overflow-wrap:anywhere}</style><h1>Project files</h1><p>' + html.escape(prefix) + '</p><ul>' + ''.join(links) + '</ul>', headers=HEADERS)
