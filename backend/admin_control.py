"""Serve the compiled admin UI only after the GitHub owner has signed in."""

import base64
import hashlib
from html import escape
import os
from pathlib import Path
import re
import secrets
import time
from urllib.parse import parse_qs, urlsplit

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from starlette.concurrency import run_in_threadpool


SESSION_SECONDS = 60 * 60
COOKIE = "__Secure-roddy-control"
LOGIN_SCRIPT = "if(location.hash)document.querySelector('[name=fragment]').value=location.hash;"
LOGIN_SCRIPT_HASH = base64.b64encode(hashlib.sha256(LOGIN_SCRIPT.encode()).digest()).decode()
PRIVATE_HEADERS = {"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"}


def register_admin_control(app, verify_admin, public_url):
    root = Path(os.getenv("STORE_ADMIN_DIR", "/var/lib/roddy-store/admin-ui")).resolve()
    sessions = {}
    parsed = urlsplit(public_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    def is_signed_in(request):
        return sessions.get(request.cookies.get(COOKIE), 0) > time.monotonic()

    def login_page(message="", fragment="", status=200):
        notice = f'<p role="alert">{escape(message)}</p>' if message else ""
        fragment = escape(fragment, quote=True)
        return HTMLResponse(f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RODDY Staff Sign-in</title>
<style>
:root{{color-scheme:dark}}body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#171715;font:1rem/1.6 system-ui;color:#f5eddf}}
main{{max-width:26rem;width:min(84vw,26rem);padding:2rem;box-sizing:border-box;background:#22211e;border:1px solid #514a40;border-radius:.6rem}}
h1{{margin:0 0 1rem}}label,input,button{{display:block}}label{{font-weight:600}}input,button{{box-sizing:border-box;width:100%;padding:.65rem;margin:.5rem 0 .8rem;font:inherit}}
button{{background:#d94d42;border:0;color:#fff;font-weight:700;cursor:pointer}}[role=alert]{{color:#ffb8ab}}
</style>
<main><h1>RODDY Staff Sign-in</h1>{notice}
<form action="/control/session" method="post">
<label for="token">GitHub token</label>
<input id="token" name="token" type="password" maxlength="256" autocomplete="current-password" required>
<input name="fragment" type="hidden" value="{fragment}">
<button type="submit">Sign in</button>
</form></main>
<script>{LOGIN_SCRIPT}</script></html>""", status_code=status, headers={
            **PRIVATE_HEADERS,
            "Content-Security-Policy": f"default-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-{LOGIN_SCRIPT_HASH}'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
        })

    def private_file(path):
        resolved = (root / path).resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file():
            return Response(status_code=404, headers=PRIVATE_HEADERS)
        return FileResponse(resolved, headers=PRIVATE_HEADERS)

    @app.get("/control", include_in_schema=False)
    def control_redirect():
        return RedirectResponse("/control/", headers=PRIVATE_HEADERS)

    @app.get("/control/", include_in_schema=False)
    def control(request: Request):
        return private_file("admin.html") if is_signed_in(request) else login_page()

    @app.post("/control/session", include_in_schema=False)
    async def sign_in(request: Request):
        if not origin.startswith("https://") or request.headers.get("origin") != origin:
            return login_page("Open the secure sign-in page to continue.", status=403)
        if request.headers.get("content-type", "").split(";")[0] != "application/x-www-form-urlencoded":
            return login_page("Invalid sign-in request.", status=400)
        try:
            fields = parse_qs((await request.body()).decode(), max_num_fields=2)
        except (ValueError, UnicodeError):
            return login_page("Invalid sign-in request.", status=400)
        token = fields.get("token", [""])[0].strip()
        candidate = fields.get("fragment", [""])[0]
        fragment = candidate if re.fullmatch(r"#[A-Za-z0-9_-]{1,50}", candidate) else ""
        if not 1 <= len(token) <= 256 or not token.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in token):
            return login_page("Enter a valid GitHub token.", fragment, 400)
        try:
            await run_in_threadpool(verify_admin, request, f"Bearer {token}")
        except HTTPException as exc:
            return login_page("Could not verify owner access. Try again.", fragment, exc.status_code)
        now = time.monotonic()
        for session, expiry in list(sessions.items()):
            if expiry <= now:
                del sessions[session]
        sessions.pop(request.cookies.get(COOKIE), None)
        session = secrets.token_urlsafe(32)
        sessions[session] = now + SESSION_SECONDS
        response = RedirectResponse(f"/control/{fragment}", 303, headers=PRIVATE_HEADERS)
        response.set_cookie(COOKIE, session, max_age=SESSION_SECONDS, path="/control/",
                            secure=True, httponly=True, samesite="strict")
        return response

    @app.post("/control/logout", include_in_schema=False)
    def sign_out(request: Request):
        if request.headers.get("origin") != origin:
            return Response(status_code=403, headers=PRIVATE_HEADERS)
        sessions.pop(request.cookies.get(COOKIE), None)
        response = RedirectResponse("/control/", 303, headers=PRIVATE_HEADERS)
        response.delete_cookie(COOKIE, path="/control/", secure=True, httponly=True, samesite="strict")
        return response

    @app.get("/control/assets/{asset:path}", include_in_schema=False)
    def control_asset(asset: str, request: Request):
        if not is_signed_in(request):
            return Response(status_code=401, headers=PRIVATE_HEADERS)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+\.(js|css|svg|png|jpe?g|webp|woff2?)", asset):
            return Response(status_code=404, headers=PRIVATE_HEADERS)
        return private_file(f"assets/{asset}")
