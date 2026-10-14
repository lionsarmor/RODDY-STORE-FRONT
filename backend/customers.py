"""Private customer profiles and address books using existing RODDY accounts.

Contact email is not an identity proof. Never use it to claim guest orders or
reset credentials. Recovery uses a random, single-use offline recovery code.
"""
import hashlib
import hmac
import json
import secrets
import time

from fastapi import HTTPException, Request

from .commerce import address_input
from .forum import credentials, password_hash
from .newsletter_mail import email_address


def short_text(value, limit, label, required=False):
    if (not isinstance(value, str) or len(value.strip()) > limit
            or any(ord(c) < 32 for c in value) or (required and not value.strip())):
        raise HTTPException(400, f"Check {label}.")
    return value.strip()


def register_customers(app, connect, auth, require_admin, rate_limit):
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS customer_profiles (
          user INTEGER PRIMARY KEY REFERENCES forum_users(id),
          name TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '',
          recovery_digest TEXT, updated INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS customer_addresses (
          id TEXT PRIMARY KEY, user INTEGER NOT NULL REFERENCES forum_users(id),
          label TEXT NOT NULL, address TEXT NOT NULL,
          is_default INTEGER NOT NULL DEFAULT 0, created INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS customer_address_owner ON customer_addresses(user);
        CREATE UNIQUE INDEX IF NOT EXISTS customer_one_default
          ON customer_addresses(user) WHERE is_default=1;
        """)

    def member(request, write=False):
        if write:
            auth["write_origin"](request)
        rate_limit(request, "customer-write" if write else "customer-read", 30 if write else 60)
        return auth["member"](request)

    def addresses(db, uid):
        return [{"id": r["id"], "label": r["label"], "default": bool(r["is_default"]),
                 "address": json.loads(r["address"])} for r in db.execute(
                     "SELECT * FROM customer_addresses WHERE user=? ORDER BY is_default DESC,created,id", (uid,))]

    def profile(db, user):
        row = db.execute("SELECT * FROM customer_profiles WHERE user=?", (user["id"],)).fetchone()
        return {"handle": user["handle"], "name": row["name"] if row else "",
                "email": row["email"] if row else "",
                "hasRecoveryCode": bool(row and row["recovery_digest"]),
                "addresses": addresses(db, user["id"])}

    @app.get("/customer/me")
    def me(request: Request):
        user = member(request)
        with connect() as db:
            return profile(db, user)

    @app.post("/customer/me")
    def save_profile(request: Request, body: dict):
        user = member(request, True)
        name = short_text(body.get("name", ""), 160, "your name", True)
        email = email_address(body.get("email", ""))
        with connect() as db:
            db.execute("INSERT INTO customer_profiles(user,name,email,updated) VALUES(?,?,?,?) "
                       "ON CONFLICT(user) DO UPDATE SET name=excluded.name,email=excluded.email,updated=excluded.updated",
                       (user["id"], name, email, int(time.time())))
            return profile(db, user)

    @app.post("/customer/addresses")
    def save_address(request: Request, body: dict):
        user = member(request, True)
        label = short_text(body.get("label", "Home"), 40, "the address label", True)
        address = address_input(body.get("address"))
        aid = short_text(body.get("id", ""), 50, "the address reference")
        default = body.get("default", False)
        if type(default) is not bool:
            raise HTTPException(400, "Choose a default address.")
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM customer_addresses WHERE id=? AND user=?", (aid, user["id"])).fetchone() if aid else None
            if aid and not existing:
                raise HTTPException(404, "Address not found.")
            count = db.execute("SELECT COUNT(*) FROM customer_addresses WHERE user=?", (user["id"],)).fetchone()[0]
            if not existing and count >= 10:
                raise HTTPException(400, "You can save up to 10 addresses. Remove one first.")
            db.execute("INSERT OR IGNORE INTO customer_profiles(user,name,email,updated) VALUES(?,?,?,?)",
                       (user["id"], address["first_name"] + " " + address["last_name"], address["email"], int(time.time())))
            default = default or not count or bool(existing and existing["is_default"])
            if default:
                db.execute("UPDATE customer_addresses SET is_default=0 WHERE user=?", (user["id"],))
            if existing:
                db.execute("UPDATE customer_addresses SET label=?,address=?,is_default=? WHERE id=? AND user=?",
                           (label, json.dumps(address), int(default), aid, user["id"]))
            else:
                aid = secrets.token_urlsafe(16)
                db.execute("INSERT INTO customer_addresses VALUES(?,?,?,?,?,?)",
                           (aid, user["id"], label, json.dumps(address), int(default), int(time.time())))
            return {"id": aid, "addresses": addresses(db, user["id"])}

    @app.post("/customer/addresses/{aid}/delete")
    def delete_address(aid: str, request: Request, body: dict):
        user = member(request, True)
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            found = db.execute("SELECT * FROM customer_addresses WHERE id=? AND user=?", (aid, user["id"])).fetchone()
            if not found:
                raise HTTPException(404, "Address not found.")
            db.execute("DELETE FROM customer_addresses WHERE id=? AND user=?", (aid, user["id"]))
            if found["is_default"]:
                db.execute("UPDATE customer_addresses SET is_default=1 WHERE id=(SELECT id FROM customer_addresses WHERE user=? ORDER BY created,id LIMIT 1)", (user["id"],))
            return {"addresses": addresses(db, user["id"])}

    def check_password(user, value):
        _, password = credentials({"handle": user["handle"], "password": value})
        if not user["password_hash"] or not hmac.compare_digest(password_hash(password, user["salt"]), user["password_hash"]):
            raise HTTPException(401, "Current password is incorrect.")

    @app.post("/customer/recovery-code")
    def recovery_code(request: Request, body: dict):
        user = member(request, True)
        rate_limit(request, "customer-security", 6)
        check_password(user, body.get("password"))
        code = secrets.token_urlsafe(32)
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT password_hash FROM forum_users WHERE id=?", (user["id"],)).fetchone()
            if not hmac.compare_digest(current[0], user["password_hash"]):
                raise HTTPException(409, "Credentials changed. Sign in again.")
            db.execute("INSERT INTO customer_profiles(user,recovery_digest,updated) VALUES(?,?,?) "
                       "ON CONFLICT(user) DO UPDATE SET recovery_digest=excluded.recovery_digest,updated=excluded.updated",
                       (user["id"], hashlib.sha256(code.encode()).hexdigest(), int(time.time())))
        return {"recoveryCode": code}

    @app.post("/customer/password")
    def change_password(request: Request, body: dict):
        user = member(request, True)
        rate_limit(request, "customer-security", 6)
        check_password(user, body.get("password"))
        _, password = credentials({"handle": user["handle"], "password": body.get("newPassword")})
        salt = secrets.token_bytes(16)
        hashed = password_hash(password, salt)
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            # Prevent concurrent credential changes using an already-replaced password.
            current = db.execute("SELECT password_hash FROM forum_users WHERE id=?", (user["id"],)).fetchone()
            if not hmac.compare_digest(current[0], user["password_hash"]):
                raise HTTPException(409, "Credentials changed. Sign in again.")
            db.execute("UPDATE forum_users SET salt=?,password_hash=? WHERE id=?", (salt, hashed, user["id"]))
            db.execute("DELETE FROM forum_sessions WHERE user=?", (user["id"],))
            db.execute("UPDATE customer_profiles SET recovery_digest=NULL WHERE user=?", (user["id"],))
            return auth["sign_in"](db, user)

    @app.post("/customer/recover")
    def recover(request: Request, body: dict):
        auth["write_origin"](request)
        rate_limit(request, "customer-recover", 5)
        handle, password = credentials({"handle": body.get("handle"), "password": body.get("newPassword")})
        code = short_text(body.get("recoveryCode", ""), 100, "your recovery code", True)
        salt = secrets.token_bytes(16)
        hashed = password_hash(password, salt)
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            user = db.execute("SELECT u.*,p.recovery_digest FROM forum_users u LEFT JOIN customer_profiles p ON u.id=p.user WHERE u.handle_key=?", (handle.lower(),)).fetchone()
            digest = hashlib.sha256(code.encode()).hexdigest()
            if not user or user["banned"] or not hmac.compare_digest(user["recovery_digest"] or "0" * 64, digest):
                raise HTTPException(401, "Handle or recovery code is incorrect.")
            db.execute("UPDATE forum_users SET salt=?,password_hash=? WHERE id=?", (salt, hashed, user["id"]))
            db.execute("UPDATE customer_profiles SET recovery_digest=NULL WHERE user=?", (user["id"],))
            db.execute("DELETE FROM forum_sessions WHERE user=?", (user["id"],))
            return auth["sign_in"](db, user)

    @app.get("/admin/customers")
    def customers(request: Request, search: str = "", before: int = 0):
        require_admin(request)
        search = short_text(search, 160, "the search")
        if not 0 <= before <= 9223372036854775807:
            raise HTTPException(400, "Invalid customer page.")
        with connect() as db:
            rows = db.execute("SELECT u.id,u.handle,p.name,p.email,p.updated FROM customer_profiles p JOIN forum_users u ON u.id=p.user "
                              "WHERE (?=0 OR u.id<?) AND (?='' OR instr(lower(u.handle || ' ' || p.name || ' ' || p.email),lower(?))>0) "
                              "ORDER BY u.id DESC LIMIT 51", (before, before, search, search)).fetchall()
            return {"customers": [{**dict(r), "addresses": addresses(db, r["id"])} for r in rows[:50]],
                    "hasMore": len(rows) > 50}
