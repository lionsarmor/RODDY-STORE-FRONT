"""One public discussion board, password handles and owner moderation."""
import hashlib
import hmac
import re
import secrets
import time

from fastapi import HTTPException, Request


def message(value, maximum, label):
    if (not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum
            or any(ord(c) < 32 and c not in "\n\t" for c in value)):
        raise HTTPException(400, f"Enter {label} (up to {maximum} characters).")
    return value.strip()


def credentials(body):
    handle = body.get("handle", "")
    password = body.get("password", "")
    if not isinstance(handle, str) or not re.fullmatch(r"[A-Za-z0-9_]{3,24}", handle):
        raise HTTPException(400, "Handles use 3–24 letters, numbers or underscores.")
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise HTTPException(400, "Use a password between 8 and 128 characters.")
    return handle, password


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)


def register_forum(app, connect, require_admin, rate_limit, origins):
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS forum_users (
          id INTEGER PRIMARY KEY, handle TEXT NOT NULL, handle_key TEXT NOT NULL UNIQUE,
          salt BLOB, password_hash BLOB, banned INTEGER NOT NULL DEFAULT 0,
          created INTEGER NOT NULL, last_post INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS forum_sessions (
          digest TEXT PRIMARY KEY, user INTEGER NOT NULL REFERENCES forum_users(id),
          expires INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS forum_topics (
          id INTEGER PRIMARY KEY, title TEXT NOT NULL, author INTEGER NOT NULL REFERENCES forum_users(id),
          body TEXT NOT NULL, created INTEGER NOT NULL, updated INTEGER NOT NULL,
          hidden INTEGER NOT NULL DEFAULT 0, locked INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS forum_replies (
          id INTEGER PRIMARY KEY, topic INTEGER NOT NULL REFERENCES forum_topics(id),
          author INTEGER NOT NULL REFERENCES forum_users(id), body TEXT NOT NULL,
          created INTEGER NOT NULL, hidden INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS forum_replies_topic ON forum_replies(topic,id);
        CREATE INDEX IF NOT EXISTS forum_topics_activity ON forum_topics(updated,id);
        """)
        # The owner writes through the existing GitHub-authenticated admin UI.
        # This reserved handle has no public password/session.
        db.execute("INSERT OR IGNORE INTO forum_users(handle,handle_key,created) VALUES('RODDY','roddy',?)", (int(time.time()),))

    def write_origin(request):
        if request.headers.get("origin") not in origins:
            raise HTTPException(403, "Start from the RODDY contact page.")

    def member(request):
        header = request.headers.get("authorization", "")
        token = header.removeprefix("Bearer ")
        if not header.startswith("Bearer ") or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise HTTPException(401, "Sign in to your forum handle first.")
        digest = hashlib.sha256(token.encode()).hexdigest()
        with connect() as db:
            row = db.execute("SELECT u.* FROM forum_sessions s JOIN forum_users u ON u.id=s.user WHERE s.digest=? AND s.expires>? AND u.banned=0", (digest, int(time.time()))).fetchone()
        if not row:
            raise HTTPException(401, "Your forum session expired. Sign in again.")
        return dict(row)

    def sign_in(db, user):
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        db.execute("DELETE FROM forum_sessions WHERE expires<?", (now,))
        # Bound active sessions per handle without affecting other members.
        db.execute("DELETE FROM forum_sessions WHERE user=? AND digest NOT IN (SELECT digest FROM forum_sessions WHERE user=? ORDER BY expires DESC LIMIT 4)", (user["id"], user["id"]))
        db.execute("INSERT INTO forum_sessions VALUES(?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user["id"], now + 30 * 86400))
        return {"token": token, "handle": user["handle"], "expiresAt": now + 30 * 86400}

    def topic_view(db, row, admin=False):
        result = {k: row[k] for k in ["id", "title", "handle", "created", "updated", "locked"]}
        result["owner"] = row["handle_key"] == "roddy"
        result["replyCount"] = db.execute("SELECT COUNT(*) FROM forum_replies WHERE topic=?" + ("" if admin else " AND hidden=0"), (row["id"],)).fetchone()[0]
        if admin:
            result.update(body=row["body"], hidden=row["hidden"], authorId=row["author"], banned=row["banned"])
        return result

    def get_topic(db, topic_id, admin=False):
        if not 1 <= topic_id <= 9223372036854775807:
            raise HTTPException(404, "Topic not found.")
        row = db.execute("SELECT t.*,u.handle,u.handle_key,u.banned FROM forum_topics t JOIN forum_users u ON u.id=t.author WHERE t.id=?" + ("" if admin else " AND t.hidden=0"), (topic_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Topic not found.")
        return row

    def replies_view(db, topic_id, before, admin=False):
        rows = db.execute("SELECT r.*,u.handle,u.handle_key,u.banned FROM forum_replies r JOIN forum_users u ON u.id=r.author WHERE r.topic=? AND (?=0 OR r.id<?)" + ("" if admin else " AND r.hidden=0") + " ORDER BY r.id DESC LIMIT 51", (topic_id, before, before)).fetchall()
        replies = []
        for row in reversed(rows[:50]):
            item = {k: row[k] for k in ["id", "body", "handle", "created"]}
            item["owner"] = row["handle_key"] == "roddy"
            if admin:
                item.update(hidden=row["hidden"], authorId=row["author"], banned=row["banned"])
            replies.append(item)
        return replies, len(rows) > 50

    def post(db, user, body, topic_id=None, owner=False):
        text = message(body.get("body"), 1800, "a message")
        title = message(body.get("title"), 100, "a topic title") if topic_id is None else None
        now = int(time.time())
        db.execute("BEGIN IMMEDIATE")
        current = db.execute("SELECT * FROM forum_users WHERE id=?", (user["id"],)).fetchone()
        if current["banned"]:
            raise HTTPException(403, "This handle cannot post. Contact RODDY privately for help.")
        if not owner and current["last_post"] > now - 30:
            raise HTTPException(429, "Wait 30 seconds between forum posts.")
        if topic_id is None:
            result = db.execute("INSERT INTO forum_topics(title,author,body,created,updated) VALUES(?,?,?,?,?)", (title, user["id"], text, now, now))
            topic_id = result.lastrowid
        else:
            topic = get_topic(db, topic_id)
            if topic["locked"]:
                raise HTTPException(409, "This topic is closed to new replies.")
            db.execute("INSERT INTO forum_replies(topic,author,body,created) VALUES(?,?,?,?)", (topic_id, user["id"], text, now))
            db.execute("UPDATE forum_topics SET updated=? WHERE id=?", (now, topic_id))
        db.execute("UPDATE forum_users SET last_post=? WHERE id=?", (now, user["id"]))
        return {"topicId": topic_id}

    @app.post("/forum/register")
    def register(request: Request, body: dict):
        write_origin(request)
        rate_limit(request, "forum-register", 3)
        handle, password = credentials(body)
        if handle.lower() in {"roddy", "admin", "administrator", "moderator", "support", "lionsarmor"}:
            raise HTTPException(409, "That handle is reserved. Choose another.")
        salt = secrets.token_bytes(16)
        hashed = password_hash(password, salt)
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM forum_users WHERE handle_key=?", (handle.lower(),)).fetchone():
                raise HTTPException(409, "That handle is taken. Sign in or choose another.")
            result = db.execute("INSERT INTO forum_users(handle,handle_key,salt,password_hash,created) VALUES(?,?,?,?,?)", (handle, handle.lower(), salt, hashed, int(time.time())))
            return sign_in(db, {"id": result.lastrowid, "handle": handle})

    @app.post("/forum/login")
    def login(request: Request, body: dict):
        write_origin(request)
        rate_limit(request, "forum-login", 6)
        handle, password = credentials(body)
        with connect() as db:
            user = db.execute("SELECT * FROM forum_users WHERE handle_key=?", (handle.lower(),)).fetchone()
            actual = password_hash(password, user["salt"] if user and user["salt"] else bytes(16))
            if not user or user["banned"] or not user["password_hash"] or not hmac.compare_digest(actual, user["password_hash"]):
                raise HTTPException(401, "Handle or password is incorrect.")
            return sign_in(db, user)

    @app.get("/forum/me")
    def me(request: Request):
        rate_limit(request, "forum-me", 30)
        user = member(request)
        return {"handle": user["handle"]}

    @app.post("/forum/logout")
    def logout(request: Request, body: dict):
        write_origin(request)
        rate_limit(request, "forum-logout", 10)
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        with connect() as db:
            db.execute("DELETE FROM forum_sessions WHERE digest=?", (hashlib.sha256(token.encode()).hexdigest(),))
        return {"saved": True}

    @app.get("/forum/topics")
    def topics(request: Request, before: int = 0):
        rate_limit(request, "forum-read", 60)
        if not 0 <= before <= 9223372036854775807:
            raise HTTPException(400, "Invalid topic page.")
        with connect() as db:
            rows = db.execute("SELECT t.*,u.handle,u.handle_key FROM forum_topics t JOIN forum_users u ON u.id=t.author WHERE t.hidden=0 AND (?=0 OR t.id<?) ORDER BY t.id DESC LIMIT 21", (before, before)).fetchall()
            return {"topics": [topic_view(db, r) for r in rows[:20]], "hasMore": len(rows) > 20}

    @app.get("/forum/topics/{topic_id}")
    def topic(topic_id: int, request: Request, before: int = 0):
        rate_limit(request, "forum-read", 60)
        if not 0 <= before <= 9223372036854775807:
            raise HTTPException(400, "Invalid reply page.")
        with connect() as db:
            row = get_topic(db, topic_id)
            replies, more = replies_view(db, topic_id, before)
            return {"topic": {**topic_view(db, row), "body": row["body"]}, "replies": replies, "hasMore": more}

    @app.post("/forum/topics")
    def new_topic(request: Request, body: dict):
        write_origin(request)
        rate_limit(request, "forum-post", 5)
        user = member(request)
        with connect() as db:
            return post(db, user, body)

    @app.post("/forum/topics/{topic_id}/replies")
    def new_reply(topic_id: int, request: Request, body: dict):
        write_origin(request)
        rate_limit(request, "forum-post", 5)
        user = member(request)
        with connect() as db:
            return post(db, user, body, topic_id)

    @app.get("/admin/forum/topics")
    def admin_topics(request: Request, before: int = 0):
        require_admin(request)
        if not 0 <= before <= 9223372036854775807:
            raise HTTPException(400, "Invalid topic page.")
        with connect() as db:
            rows = db.execute("SELECT t.*,u.handle,u.handle_key,u.banned FROM forum_topics t JOIN forum_users u ON u.id=t.author WHERE (?=0 OR t.id<?) ORDER BY t.id DESC LIMIT 21", (before, before)).fetchall()
            return {"topics": [topic_view(db, r, True) for r in rows[:20]], "hasMore": len(rows) > 20}

    @app.get("/admin/forum/topics/{topic_id}")
    def admin_topic(topic_id: int, request: Request, before: int = 0):
        require_admin(request)
        if not 0 <= before <= 9223372036854775807:
            raise HTTPException(400, "Invalid reply page.")
        with connect() as db:
            row = get_topic(db, topic_id, True)
            replies, more = replies_view(db, topic_id, before, True)
            return {"topic": topic_view(db, row, True), "replies": replies, "hasMore": more}

    @app.post("/admin/forum/topics")
    def owner_topic(request: Request, body: dict):
        require_admin(request)
        with connect() as db:
            owner = db.execute("SELECT * FROM forum_users WHERE handle_key='roddy'").fetchone()
            return post(db, owner, body, owner=True)

    @app.post("/admin/forum/topics/{topic_id}/replies")
    def owner_reply(topic_id: int, request: Request, body: dict):
        require_admin(request)
        with connect() as db:
            owner = db.execute("SELECT * FROM forum_users WHERE handle_key='roddy'").fetchone()
            return post(db, owner, body, topic_id, owner=True)

    @app.post("/admin/forum/topics/{topic_id}/moderate")
    def moderate_topic(topic_id: int, request: Request, body: dict):
        require_admin(request)
        if not body or any(k not in {"hidden", "locked"} or type(v) is not bool for k, v in body.items()):
            raise HTTPException(400, "Choose visibility or reply status.")
        with connect() as db:
            get_topic(db, topic_id, True)
            for key, value in body.items():
                db.execute(f"UPDATE forum_topics SET {key}=? WHERE id=?", (int(value), topic_id))
        return {"saved": True}

    @app.post("/admin/forum/replies/{reply_id}/moderate")
    def moderate_reply(reply_id: int, request: Request, body: dict):
        require_admin(request)
        if not 1 <= reply_id <= 9223372036854775807:
            raise HTTPException(404, "Reply not found.")
        if set(body) != {"hidden"} or type(body["hidden"]) is not bool:
            raise HTTPException(400, "Choose reply visibility.")
        with connect() as db:
            if not db.execute("SELECT 1 FROM forum_replies WHERE id=?", (reply_id,)).fetchone():
                raise HTTPException(404, "Reply not found.")
            db.execute("UPDATE forum_replies SET hidden=? WHERE id=?", (int(body["hidden"]), reply_id))
        return {"saved": True}

    @app.post("/admin/forum/users/{user_id}/moderate")
    def moderate_user(user_id: int, request: Request, body: dict):
        require_admin(request)
        if not 1 <= user_id <= 9223372036854775807:
            raise HTTPException(404, "Handle not found.")
        if set(body) != {"banned"} or type(body["banned"]) is not bool:
            raise HTTPException(400, "Choose handle posting access.")
        with connect() as db:
            user = db.execute("SELECT * FROM forum_users WHERE id=?", (user_id,)).fetchone()
            if not user or user["handle_key"] == "roddy":
                raise HTTPException(409, "This handle cannot be moderated.")
            db.execute("UPDATE forum_users SET banned=? WHERE id=?", (int(body["banned"]), user_id))
            db.execute("DELETE FROM forum_sessions WHERE user=?", (user_id,))
        return {"saved": True}
