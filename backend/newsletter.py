"""Private newsletter drafts and explicit opt-ins for owner-operated email delivery."""
import csv
import hashlib
import io
import json
import time
import uuid

from fastapi import HTTPException, Request
from fastapi.responses import Response

from .newsletter_mail import content_input, email_address, render, text

CONSENT = "I want occasional RODDY email updates, new releases and offers. I can unsubscribe by replying to any newsletter."
UNSUBSCRIBE = "mailto:support@roddy.world?subject=Unsubscribe%20from%20RODDY"


def register_newsletter(app, connect, require_admin, rate_limit, origins):
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS newsletter_subscribers (
          id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE,
          status TEXT NOT NULL DEFAULT 'active', created INTEGER NOT NULL,
          updated INTEGER NOT NULL, consent TEXT NOT NULL, source TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS newsletter_settings (
          id INTEGER PRIMARY KEY CHECK(id=1), postal_address TEXT NOT NULL DEFAULT ''
        );
        INSERT OR IGNORE INTO newsletter_settings(id) VALUES(1);
        CREATE TABLE IF NOT EXISTS newsletter_campaigns (
          id TEXT PRIMARY KEY, content TEXT NOT NULL, revision INTEGER NOT NULL,
          created INTEGER NOT NULL, updated INTEGER NOT NULL,
          sent_at INTEGER, sent_count INTEGER, sent_audience TEXT
        );
        """)

    def settings(db):
        return {"postalAddress": db.execute("SELECT postal_address FROM newsletter_settings WHERE id=1").fetchone()[0]}

    def campaign(db, identifier):
        if not isinstance(identifier, str) or len(identifier) > 64:
            raise HTTPException(400, "Invalid newsletter draft.")
        row = db.execute("SELECT * FROM newsletter_campaigns WHERE id=?", (identifier,)).fetchone()
        if not row:
            raise HTTPException(404, "Newsletter draft not found.")
        return {"id": row["id"], "content": json.loads(row["content"]), "revision": row["revision"],
                "created": row["created"], "updated": row["updated"], "sentAt": row["sent_at"], "sentCount": row["sent_count"]}

    def audience(db):
        rows = db.execute("SELECT id,email,updated FROM newsletter_subscribers WHERE status='active' ORDER BY id").fetchall()
        digest = hashlib.sha256(json.dumps([tuple(row) for row in rows]).encode()).hexdigest()
        return rows, digest

    @app.post("/newsletter/subscribe")
    def subscribe(request: Request, body: dict):
        if request.headers.get("origin") not in origins:
            raise HTTPException(403, "Please sign up from the RODDY website.")
        rate_limit(request, "newsletter-signup", 3)
        message = {"message": "Thanks! Your request is saved. We send occasional updates; reply to any newsletter to unsubscribe."}
        if body.get("company"):
            return message
        if body.get("consent") is not True:
            raise HTTPException(400, "Please agree to receive occasional RODDY emails.")
        email = email_address(body.get("email"))
        now = int(time.time())
        with connect() as db:
            # Explicit single opt-in. Never silently reactivate a suppressed address.
            db.execute("INSERT OR IGNORE INTO newsletter_subscribers(email,created,updated,consent,source) VALUES(?,?,?,?,?)",
                       (email, now, now, CONSENT, "website"))
        return message

    @app.get("/admin/newsletters")
    def overview(request: Request):
        require_admin(request)
        with connect() as db:
            counts = dict(db.execute("SELECT status,count(*) FROM newsletter_subscribers GROUP BY status").fetchall())
            drafts = [campaign(db, row[0]) for row in db.execute("SELECT id FROM newsletter_campaigns ORDER BY updated DESC,id LIMIT 100").fetchall()]
            return {"settings": settings(db), "counts": counts, "campaigns": drafts}

    @app.post("/admin/newsletters/settings")
    def save_settings(request: Request, body: dict):
        require_admin(request)
        address = text(body.get("postalAddress", ""), 500, "your business mailing address")
        with connect() as db:
            db.execute("UPDATE newsletter_settings SET postal_address=? WHERE id=1", (address,))
            return {"settings": settings(db)}

    @app.get("/admin/newsletters/subscribers")
    def subscribers(request: Request, page: int = 1, search: str = ""):
        require_admin(request)
        if not 1 <= page <= 100000 or len(search) > 254:
            raise HTTPException(400, "Check the subscriber search or page.")
        with connect() as db:
            rows = db.execute("SELECT id,email,status,created,consent FROM newsletter_subscribers WHERE instr(email,?)>0 ORDER BY id DESC LIMIT 51 OFFSET ?",
                              (search.strip().lower(), (page - 1) * 50)).fetchall()
        return {"subscribers": [dict(row) for row in rows[:50]], "hasMore": len(rows) > 50}

    @app.post("/admin/newsletters/subscribers/unsubscribe")
    def suppress(request: Request, body: dict):
        require_admin(request)
        email = email_address(body.get("email"))
        now = int(time.time())
        with connect() as db:
            # Also record requests from someone not currently on the list.
            db.execute("INSERT INTO newsletter_subscribers(email,status,created,updated,consent,source) VALUES(?,'unsubscribed',?,?,'','owner-request') ON CONFLICT(email) DO UPDATE SET status='unsubscribed',updated=excluded.updated",
                       (email, now, now))
        return {"saved": True}

    @app.get("/admin/newsletters/subscribers.csv")
    def csv_export(request: Request):
        require_admin(request)
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["email", "status", "opted_in_at", "consent"])
        with connect() as db:
            for row in db.execute("SELECT email,status,created,consent FROM newsletter_subscribers ORDER BY id"):
                writer.writerow(["'" + str(value) if str(value).startswith(("=", "+", "-", "@", "\t", "\r")) else value for value in row])
        return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="RODDY-newsletter-subscribers.csv"'})

    @app.post("/admin/newsletters/drafts")
    def save_draft(request: Request, body: dict):
        require_admin(request)
        content = content_input(body.get("content"))
        identifier = body.get("id") or uuid.uuid4().hex
        if not isinstance(identifier, str) or len(identifier) > 64:
            raise HTTPException(400, "Invalid newsletter draft.")
        now = int(time.time())
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if body.get("id"):
                current = campaign(db, identifier)
                if current["sentAt"]:
                    raise HTTPException(409, "This edition is recorded as sent. Duplicate it to start another.")
                if body.get("revision") != current["revision"]:
                    raise HTTPException(409, "Someone changed this draft. Your edits are still here; save them as a new copy or reload the saved edition.")
                db.execute("UPDATE newsletter_campaigns SET content=?,revision=revision+1,updated=? WHERE id=?", (json.dumps(content), now, identifier))
            else:
                db.execute("INSERT INTO newsletter_campaigns(id,content,revision,created,updated) VALUES(?,?,1,?,?)", (identifier, json.dumps(content), now, now))
            return {"campaign": campaign(db, identifier)}

    @app.post("/admin/newsletters/preview")
    def preview(request: Request, body: dict):
        require_admin(request)
        content = content_input(body.get("content"))
        with connect() as db:
            html, plain = render(content, settings(db), UNSUBSCRIBE)
        return {"html": html, "text": plain}

    @app.post("/admin/newsletters/prepare")
    def prepare(request: Request, body: dict):
        require_admin(request)
        with connect() as db:
            edition = campaign(db, body.get("id", ""))
            if body.get("revision") != edition["revision"]:
                raise HTTPException(409, "Reload the current saved draft before preparing recipients.")
            config = settings(db)
            if not config["postalAddress"]:
                raise HTTPException(409, "Add a valid business mailing address or PO box in newsletter settings before preparing advertising email.")
            rows, digest = audience(db)
            html, plain = render(edition["content"], config, UNSUBSCRIBE)
        emails = [row["email"] for row in rows]
        return {"html": html, "text": plain, "subject": edition["content"]["subject"],
                "count": len(emails), "audienceHash": digest, "revision": edition["revision"],
                "batches": [", ".join(emails[n:n + 50]) for n in range(0, len(emails), 50)]}

    @app.post("/admin/newsletters/record-sent")
    def record_sent(request: Request, body: dict):
        require_admin(request)
        if body.get("confirmedManualSend") is not True:
            raise HTTPException(400, "Record this only after you have sent every batch in your email account.")
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            edition = campaign(db, body.get("id", ""))
            rows, digest = audience(db)
            if body.get("revision") != edition["revision"] or body.get("audienceHash") != digest:
                raise HTTPException(409, "The draft or subscriber list changed. Refresh the export and check which batches you sent before recording this edition.")
            if not rows or not settings(db)["postalAddress"]:
                raise HTTPException(409, "A mailing address and active subscribers are required.")
            if not edition["sentAt"]:
                db.execute("UPDATE newsletter_campaigns SET sent_at=?,sent_count=?,sent_audience=? WHERE id=?",
                           (int(time.time()), len(rows), json.dumps([row["id"] for row in rows]), edition["id"]))
        return {"saved": True}
