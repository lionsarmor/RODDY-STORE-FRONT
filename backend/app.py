"""Small, digital-only checkout and private-file delivery service for the droplet."""

import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .square import Square, PaymentUnavailable


def checkout_url(value):
    url = urlsplit(value)
    return (url.scheme == "https" and not url.username and not url.password
            and url.hostname in {"square.link", "checkout.square.site", "sandbox.square.link"})


def create_app(*, database=None, private_dir=None, manifest=None, provider=None,
               catalog_loader=None, enabled=None, site=None, public_url=None):
    database = Path(database or os.getenv("STORE_DATABASE", "/var/lib/roddy-store/orders.sqlite3"))
    private_dir = Path(private_dir or os.getenv("STORE_PRIVATE_DIR", "/var/lib/roddy-store/files")).resolve()
    manifest = manifest or os.getenv("STORE_MANIFEST", "/etc/roddy-store/digital-products.json")
    site = (site or os.getenv("SITE_URL", "https://roddy.world")).rstrip("/")
    public_url = (public_url or os.getenv("STORE_PUBLIC_URL", "")).rstrip("/")
    enabled = enabled if enabled is not None else os.getenv("STORE_CHECKOUT_ENABLED", "false") == "true"
    provider = provider or Square(os.getenv("SQUARE_ACCESS_TOKEN", ""),
                                  os.getenv("SQUARE_LOCATION_ID", ""),
                                  os.getenv("SQUARE_MODE", "sandbox"))
    admin_login = os.getenv("ADMIN_GITHUB_LOGIN", "lionsarmor")
    origins = os.getenv("ALLOWED_ORIGINS", "https://roddy.world,https://www.roddy.world").split(",")

    def load_catalog():
        url = os.getenv("PRODUCTS_URL", "https://raw.githubusercontent.com/lionsarmor/RODDY-STORE-FRONT/main/public/data/products.json")
        if not url.startswith("https://"):
            raise ValueError("PRODUCTS_URL must use HTTPS")
        try:
            response = httpx.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(503, "Catalog is unavailable. Please try again.") from exc

    catalog_loader = catalog_loader or load_catalog
    database.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect():
        db = sqlite3.connect(database, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    with connect() as db:
        db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS orders (
          request_id TEXT PRIMARY KEY, session TEXT NOT NULL UNIQUE,
          cart TEXT NOT NULL, items TEXT NOT NULL, amount INTEGER NOT NULL,
          created INTEGER NOT NULL, provider_id TEXT, url TEXT, paid INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tickets (
          digest TEXT PRIMARY KEY, session TEXT NOT NULL REFERENCES orders(session),
          product TEXT NOT NULL, expires INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS limits (
          bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, expires INTEGER NOT NULL
        );
        """)
    os.chmod(database, 0o600)

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=origins,
                       allow_methods=["POST", "GET"], allow_headers=["content-type", "authorization"])

    @app.middleware("http")
    async def headers(request, call_next):
        # No API endpoint accepts a body larger than a small cart. Reject before parsing.
        if request.method == "POST":
            body = await request.body()
            if len(body) > 8192:
                return JSONResponse({"error": "Request too large."}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(HTTPException)
    async def http_error(_, exc):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_, exc):
        return JSONResponse({"error": "Invalid request."}, status_code=422)

    @app.exception_handler(PaymentUnavailable)
    async def provider_error(_, exc):
        return JSONResponse({"error": str(exc)}, status_code=503)

    def rate_limit(request, kind, maximum):
        # systemd runs one uvicorn process; SQLite makes limits durable across restarts.
        # Caddy strips spoofed forwarded headers; uvicorn trusts only loopback proxies.
        address = request.client.host if request.client else "unknown"
        now = int(time.time())
        bucket = hashlib.sha256(f"{kind}:{address}:{now // 60}".encode()).hexdigest()
        with connect() as db:
            db.execute("DELETE FROM limits WHERE expires < ?", (now,))
            db.execute("INSERT INTO limits VALUES (?, 1, ?) ON CONFLICT(bucket) DO UPDATE SET count=count+1",
                       (bucket, now + 120))
            count = db.execute("SELECT count FROM limits WHERE bucket=?", (bucket,)).fetchone()[0]
        if count > maximum:
            raise HTTPException(429, "Too many requests. Please try again in a minute.")

    def assets():
        try:
            data = manifest if isinstance(manifest, dict) else json.loads(Path(manifest).read_text())
            if not isinstance(data, dict):
                raise ValueError()
            return data
        except (OSError, ValueError) as exc:
            raise HTTPException(503, "Digital delivery is not configured yet.") from exc

    def private_file(item):
        if provider.mode == "sandbox" and not item.get("sandbox"):
            raise HTTPException(503, "Sandbox checkout requires a test-only download file.")
        filename = item.get("file", "")
        checksum = item.get("sha256", "")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.zip", filename):
            raise HTTPException(503, "Invalid digital delivery configuration.")
        path = (private_dir / filename).resolve()
        if (path.parent != private_dir or not path.is_file()
                or not re.fullmatch(r"[a-f0-9]{64}", checksum)
                or hashlib.sha256(path.read_bytes()).hexdigest() != checksum):
            raise HTTPException(503, "The download is temporarily unavailable. Please contact RODDY.")
        return path

    def normalize_cart(body):
        raw = body.get("items") if isinstance(body, dict) else None
        if not isinstance(raw, list) or not 1 <= len(raw) <= 10:
            raise HTTPException(400, "Choose at least one paid digital product.")
        ids = []
        for item in raw:
            if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
                    or type(item.get("qty")) is not int or item["qty"] != 1
                    or item["id"] in ids):
                raise HTTPException(400, "Digital downloads allow one copy of each product per order.")
            ids.append(item["id"])
        return json.dumps(sorted(ids))

    def price_cart(cart):
        products = {p["id"]: p for p in catalog_loader()["products"]}
        files = assets()
        items = []
        for product_id in json.loads(cart):
            p = products.get(product_id)
            if (not p or not p.get("active") or p.get("status") != "available"
                    or p.get("pricePending") or p.get("type") != "digital"
                    or p.get("downloadUrl") or "free" in p.get("tags", [])
                    or p.get("trackStock", True) or product_id not in files):
                raise HTTPException(409, "An item is unavailable for paid digital checkout.")
            price = p.get("price")
            if type(price) not in (float, int) or not 0 < price <= 999999:
                raise HTTPException(409, "Invalid product price.")
            cents = round(price * 100)
            if cents < 1 or abs(price * 100 - cents) > 0.00001:
                raise HTTPException(409, "Invalid product price.")
            item = {"id": product_id, "name": p["name"], "cents": cents, **files[product_id]}
            # The manifest only specifies server-owned filenames and hashes.
            item.update(id=product_id, name=p["name"], cents=cents)
            private_file(item)
            items.append(item)
        return items

    def get_order(session):
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", session):
            raise HTTPException(404, "Order not found.")
        with connect() as db:
            row = db.execute("SELECT * FROM orders WHERE session=?", (session,)).fetchone()
        if not row:
            raise HTTPException(404, "Order not found.")
        if row["created"] < time.time() - 30 * 86400:
            raise HTTPException(410, "This order link has expired. Contact RODDY with your payment receipt.")
        return dict(row)

    def verify(order):
        paid = bool(order["provider_id"] and provider.paid(order["provider_id"], order["amount"]))
        with connect() as db:
            db.execute("UPDATE orders SET paid=? WHERE session=?", (int(paid), order["session"]))
        return paid

    @app.get("/health")
    def health(request: Request):
        rate_limit(request, "health", 10)
        configured = provider.configured
        account_ready = provider.check_account() if configured else False
        return {"provider": provider.name, "configured": configured,
                "accountReady": account_ready, "mode": provider.mode,
                "checkoutEnabled": enabled}

    @app.post("/checkout")
    def checkout(request: Request, body: dict):
        rate_limit(request, "checkout", 10)
        if not enabled or not provider.configured or not public_url.startswith("https://"):
            raise HTTPException(503, "Online checkout is getting ready. Please check back soon.")
        if request.headers.get("origin") not in origins:
            raise HTTPException(403, "Checkout must start from the RODDY store.")
        cart = normalize_cart(body)
        try:
            request_id = str(UUID(body.get("requestId", ""), version=4))
            if request_id != body.get("requestId"):
                raise ValueError()
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(400, "Invalid checkout request reference.") from exc
        with connect() as db:
            existing = db.execute("SELECT * FROM orders WHERE request_id=?", (request_id,)).fetchone()
        if not existing:
            items = price_cart(cart)
            with connect() as db:
                db.execute("INSERT OR IGNORE INTO orders(request_id,session,cart,items,amount,created) VALUES(?,?,?,?,?,?)",
                           (request_id, secrets.token_urlsafe(32), cart, json.dumps(items),
                            sum(item["cents"] for item in items), int(time.time())))
                existing = db.execute("SELECT * FROM orders WHERE request_id=?", (request_id,)).fetchone()
        order = dict(existing)
        if order["cart"] != cart:
            raise HTTPException(409, "This checkout reference belongs to a different cart.")
        if order["created"] < time.time() - 3600:
            raise HTTPException(409, "This checkout has expired. Start a new checkout from your cart.")
        if not order["url"]:
            order["items"] = json.loads(order["items"])
            provider_id, url = provider.create_checkout(order, site + "/order.html#session_id=" + order["session"])
            if not checkout_url(url):
                raise HTTPException(503, "Payment service returned an invalid destination.")
            with connect() as db:
                db.execute("UPDATE orders SET provider_id=?,url=? WHERE request_id=?", (provider_id, url, request_id))
            order["url"] = url
        return {"url": order["url"], "provider": provider.name, "sessionId": order["session"]}

    @app.post("/order")
    def order_status(request: Request, body: dict):
        rate_limit(request, "order", 30)
        order = get_order(str(body.get("sessionId", "")))
        paid = verify(order)
        downloads = []
        now = int(time.time())
        if paid:
            with connect() as db:
                db.execute("DELETE FROM tickets WHERE expires < ?", (now,))
                for item in json.loads(order["items"]):
                    private_file(item)
                    ticket = secrets.token_urlsafe(32)
                    db.execute("INSERT INTO tickets VALUES(?,?,?,?)",
                               (hashlib.sha256(ticket.encode()).hexdigest(), order["session"], item["id"], now + 900))
                    downloads.append({"name": item["name"], "filename": item["file"],
                                      "url": public_url + "/download/" + ticket,
                                      "expiresAt": now + 900})
        return {"paid": paid, "amountTotal": order["amount"], "currency": "USD", "downloads": downloads,
                "mode": provider.mode}

    @app.get("/download/{ticket}")
    def download(request: Request, ticket: str):
        rate_limit(request, "download", 20)
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", ticket):
            raise HTTPException(404, "Download not found.")
        with connect() as db:
            row = db.execute("SELECT * FROM tickets WHERE digest=? AND expires>?",
                             (hashlib.sha256(ticket.encode()).hexdigest(), int(time.time()))).fetchone()
        if not row:
            raise HTTPException(410, "Download link expired. Check your order again for a fresh link.")
        order = get_order(row["session"])
        # Re-query Square to revoke new downloads after a refund. Never trust a cached 'paid' flag.
        if not verify(order):
            raise HTTPException(403, "Payment is not confirmed for this download.")
        item = next(i for i in json.loads(order["items"]) if i["id"] == row["product"])
        return FileResponse(private_file(item), media_type="application/zip", filename=item["file"])

    @app.get("/admin/orders")
    def admin_orders(request: Request):
        rate_limit(request, "admin", 10)
        token = request.headers.get("authorization", "")
        if not token.startswith("Bearer "):
            raise HTTPException(401, "Sign in with GitHub first.")
        try:
            response = httpx.get("https://api.github.com/user", headers={"Authorization": token}, timeout=15)
            response.raise_for_status()
            if response.json().get("login", "").lower() != admin_login.lower():
                raise HTTPException(403, "This GitHub account cannot view orders.")
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(401, "Could not verify GitHub sign-in.") from exc
        with connect() as db:
            rows = db.execute("SELECT provider_id,created,amount,paid FROM orders ORDER BY created DESC LIMIT 100").fetchall()
        return {"data": [{"id": row["provider_id"] or "not-created", "created": row["created"],
                          "amount_total": row["amount"], "currency": "USD",
                          "payment_status": "paid" if row["paid"] else "unconfirmed"} for row in rows],
                "has_more": False}

    return app
