import hashlib
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.test_checkout import FakeProvider


class ForumTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / "store.sqlite3"
        self.app = create_app(database=self.database, private_dir=self.root, manifest={},
                              provider=FakeProvider(), catalog_loader=lambda: {"products": []},
                              enabled=False, worker_enabled=False)
        self.client = TestClient(self.app)
        self.origin = {"origin": "https://roddy.world"}

    def account(self, handle="Maker_One"):
        response = self.client.post("/forum/register", headers=self.origin,
                                    json={"handle": handle, "password": "a unique test password"})
        self.assertEqual(response.status_code, 200, response.text)
        self.token = response.json()["token"]
        return {**self.origin, "authorization": "Bearer " + self.token}

    def post(self, headers, title="A good question", text="How do I get started?"):
        return self.client.post("/forum/topics", headers=headers, json={"title": title, "body": text})

    def admin(self, method, path, body=None, login="lionsarmor"):
        response = type("Response", (), {"raise_for_status": lambda _: None, "json": lambda _: {"login": login}})()
        with patch("backend.app.httpx.get", return_value=response):
            return self.client.request(method, path, json=body, headers={"authorization": "Bearer owner-test"})

    def clear_cooldown(self):
        with sqlite3.connect(self.database) as db:
            db.execute("UPDATE forum_users SET last_post=0")

    def test_anonymous_read_and_authenticated_topics_replies_persist(self):
        self.assertEqual(self.client.get("/forum/topics").json(), {"topics": [], "hasMore": False})
        self.assertEqual(self.post(self.origin).status_code, 401)
        headers = self.account()
        topic = self.post(headers, text="Line one\nLine two ☺ <script>alert(1)</script>").json()["topicId"]
        self.clear_cooldown()
        reply = self.client.post(f"/forum/topics/{topic}/replies", headers=headers, json={"body": "A helpful reply."})
        self.assertEqual(reply.status_code, 200, reply.text)
        self.assertEqual(self.client.get("/forum/topics").json()["topics"][0]["replyCount"], 1)
        # Reopen the same SQLite DB, proving this is not process-local state.
        app = create_app(database=self.database, private_dir=self.root, manifest={},
                         provider=FakeProvider(), catalog_loader=lambda: {"products": []},
                         enabled=False, worker_enabled=False)
        data = TestClient(app).get(f"/forum/topics/{topic}").json()
        self.assertIn("<script>", data["topic"]["body"])  # Stored/returned as text; Vue escapes it.
        self.assertEqual(data["replies"][0]["body"], "A helpful reply.")
        self.assertEqual(data["topic"]["handle"], "Maker_One")
        self.assertFalse(data["topic"]["owner"])

    def test_unique_case_insensitive_handle_salted_password_and_hashed_sessions(self):
        headers = self.account()
        duplicate = self.client.post("/forum/register", headers=self.origin, json={"handle": "maker_one", "password": "a unique test password"})
        self.assertEqual(duplicate.status_code, 409)
        with sqlite3.connect(self.database) as db:
            salt, stored = db.execute("SELECT salt,password_hash FROM forum_users WHERE handle_key='maker_one'").fetchone()
            digest = db.execute("SELECT digest FROM forum_sessions").fetchone()[0]
        self.assertEqual(len(salt), 16)
        self.assertEqual(len(stored), 32)
        self.assertNotEqual(stored, b"a unique test password")
        self.assertEqual(digest, hashlib.sha256(self.token.encode()).hexdigest())
        self.assertEqual(self.client.get("/forum/me", headers=headers).json(), {"handle": "Maker_One"})
        self.assertEqual(self.client.get("/forum/me", headers={"authorization": self.token}).status_code, 401)

    def test_login_expiry_logout_and_no_credentials_in_public_responses(self):
        headers = self.account()
        self.assertEqual(self.client.post("/forum/logout", headers=headers, json={}).status_code, 200)
        self.assertEqual(self.client.get("/forum/me", headers=headers).status_code, 401)
        for name in ["Maker_One", "missing_handle"]:
            bad = self.client.post("/forum/login", headers=self.origin, json={"handle": name, "password": "wrong password"})
            self.assertEqual(bad.status_code, 401)
            self.assertEqual(bad.json()["error"], "Handle or password is incorrect.")
        good = self.client.post("/forum/login", headers=self.origin, json={"handle": "MAKER_ONE", "password": "a unique test password"})
        self.assertEqual(good.status_code, 200)
        self.assertEqual(good.json()["handle"], "Maker_One")
        with sqlite3.connect(self.database) as db:
            db.execute("UPDATE forum_sessions SET expires=?", (int(time.time()) - 1,))
        self.assertEqual(self.client.get("/forum/me", headers={"authorization": "Bearer " + good.json()["token"]}).status_code, 401)

    def test_handles_and_messages_validate_bounds_and_reserved_owner(self):
        for handle, password in [("no", "good password"), ("has spaces", "good password"), ("okay", "short")]:
            self.assertEqual(self.client.post("/forum/register", headers=self.origin, json={"handle": handle, "password": password}).status_code, 400)
        # Clear request limits to inspect validation independently of throttling.
        with sqlite3.connect(self.database) as db: db.execute("DELETE FROM limits")
        for handle in ["RODDY", "ADMIN", "support"]:
            self.assertEqual(self.client.post("/forum/register", headers=self.origin, json={"handle": handle, "password": "good password"}).status_code, 409)
        with sqlite3.connect(self.database) as db: db.execute("DELETE FROM limits")
        headers = self.account()
        for title, body in [("", "ok"), ("a"*101, "ok"), ("title", "a"*1801), ("title", "bad\0text")]:
            self.assertEqual(self.post(headers, title, body).status_code, 400)
        self.assertEqual(self.post(headers).status_code, 200)

    # Keep the login burst in one minute bucket even on a slow CI runner.
    @patch("backend.app.time.time", return_value=1_800_000_000)
    def test_origin_checks_rate_limits_and_per_handle_cooldown(self, _clock):
        self.assertEqual(self.client.post("/forum/register", json={"handle": "someone", "password": "good password"}).status_code, 403)
        headers = self.account()
        self.assertEqual(self.post({**headers, "origin": "https://other.example"}).status_code, 403)
        topic = self.post(headers).json()["topicId"]
        second = self.client.post(f"/forum/topics/{topic}/replies", headers=headers, json={"body": "Too soon"})
        self.assertEqual(second.status_code, 429)
        self.clear_cooldown()
        self.assertEqual(self.client.post(f"/forum/topics/{topic}/replies", headers=headers, json={"body": "Later"}).status_code, 200)
        # Logout also needs the storefront Origin and cannot be triggered by a
        # foreign site that happens to know a public handle.
        self.assertEqual(self.client.post("/forum/logout", json={}, headers={"authorization": headers["authorization"]}).status_code, 403)
        for _ in range(7):
            attempt = self.client.post("/forum/login", headers=self.origin, json={"handle": "missing", "password": "wrong password"})
        self.assertEqual(attempt.status_code, 429)

    def test_owner_moderation_hides_restores_closes_and_revokes_banned_handle(self):
        headers = self.account()
        topic = self.post(headers).json()["topicId"]
        self.clear_cooldown()
        self.client.post(f"/forum/topics/{topic}/replies", headers=headers, json={"body": "First reply"})
        public = self.client.get(f"/forum/topics/{topic}").json()
        reply = public["replies"][0]["id"]
        self.assertEqual(self.client.get("/admin/forum/topics").status_code, 401)
        self.assertEqual(self.admin("GET", "/admin/forum/topics", login="someone-else").status_code, 403)
        self.assertEqual(self.admin("POST", f"/admin/forum/replies/{reply}/moderate", {"hidden": True}).status_code, 200)
        self.assertEqual(self.client.get(f"/forum/topics/{topic}").json()["replies"], [])
        hidden = self.admin("GET", f"/admin/forum/topics/{topic}").json()
        self.assertEqual(hidden["replies"][0]["hidden"], 1)
        self.admin("POST", f"/admin/forum/replies/{reply}/moderate", {"hidden": False})
        self.admin("POST", f"/admin/forum/topics/{topic}/moderate", {"locked": True})
        self.clear_cooldown()
        self.assertEqual(self.client.post(f"/forum/topics/{topic}/replies", headers=headers, json={"body": "Closed"}).status_code, 409)
        self.admin("POST", f"/admin/forum/topics/{topic}/moderate", {"hidden": True})
        self.assertEqual(self.client.get(f"/forum/topics/{topic}").status_code, 404)
        self.assertEqual(self.client.get("/forum/topics").json()["topics"], [])
        self.admin("POST", f"/admin/forum/topics/{topic}/moderate", {"hidden": False, "locked": False})
        self.assertEqual(self.client.get(f"/forum/topics/{topic}").status_code, 200)
        user = hidden["topic"]["authorId"]
        self.admin("POST", f"/admin/forum/users/{user}/moderate", {"banned": True})
        self.assertEqual(self.client.get("/forum/me", headers=headers).status_code, 401)
        self.assertEqual(self.client.post("/forum/login", headers=self.origin, json={"handle": "Maker_One", "password": "a unique test password"}).status_code, 401)
        self.admin("POST", f"/admin/forum/users/{user}/moderate", {"banned": False})
        self.assertEqual(self.client.post("/forum/login", headers=self.origin, json={"handle": "Maker_One", "password": "a unique test password"}).status_code, 200)

    def test_only_owner_can_post_as_roddy_and_moderation_input_is_strict(self):
        topic = self.admin("POST", "/admin/forum/topics", {"title": "Welcome", "body": "Ask away."}).json()["topicId"]
        self.assertEqual(self.client.post("/admin/forum/topics", headers=self.origin, json={"title": "Fake", "body": "Fake"}).status_code, 401)
        self.admin("POST", f"/admin/forum/topics/{topic}/replies", {"body": "Owner reply"})
        data = self.client.get(f"/forum/topics/{topic}").json()
        self.assertTrue(data["topic"]["owner"])
        self.assertTrue(data["replies"][0]["owner"])
        self.assertEqual(data["topic"]["handle"], "RODDY")
        self.assertEqual(self.admin("POST", f"/admin/forum/topics/{topic}/moderate", {"hidden": "false"}).status_code, 400)
        self.assertEqual(self.admin("POST", f"/admin/forum/topics/{topic}/moderate", {"title": "changed"}).status_code, 400)
        owner = self.admin("GET", f"/admin/forum/topics/{topic}").json()["topic"]["authorId"]
        self.assertEqual(self.admin("POST", f"/admin/forum/users/{owner}/moderate", {"banned": True}).status_code, 409)
        for field in ["authorId", "salt", "password_hash", "token", "banned"]:
            self.assertNotIn(field, data["topic"])
            self.assertNotIn(field, data["replies"][0])

    def test_public_pagination_keeps_hidden_content_out_and_latest_reply_visible(self):
        for before in [-1, 9223372036854775808]:
            self.assertEqual(self.client.get("/forum/topics", params={"before": before}).status_code, 400)
        self.assertEqual(self.client.get("/forum/topics/9223372036854775808").status_code, 404)
        now = int(time.time())
        with sqlite3.connect(self.database) as db:
            owner = db.execute("SELECT id FROM forum_users WHERE handle_key='roddy'").fetchone()[0]
            for i in range(25):
                db.execute("INSERT INTO forum_topics(title,author,body,created,updated) VALUES(?,?,?,?,?)", (f"Topic {i}", owner, "Body", now, now))
            topic = db.execute("SELECT MAX(id) FROM forum_topics").fetchone()[0]
            for i in range(55):
                db.execute("INSERT INTO forum_replies(topic,author,body,created,hidden) VALUES(?,?,?,?,?)", (topic, owner, f"Reply {i}", now, int(i==20)))
        first = self.client.get("/forum/topics").json()
        self.assertEqual(len(first["topics"]), 20)
        self.assertTrue(first["hasMore"])
        second = self.client.get("/forum/topics", params={"before": first["topics"][-1]["id"]}).json()
        self.assertEqual(len(second["topics"]), 5)
        self.assertFalse(second["hasMore"])
        recent = self.client.get(f"/forum/topics/{topic}").json()
        self.assertEqual(len(recent["replies"]), 50)
        self.assertEqual(recent["replies"][-1]["body"], "Reply 54")
        self.assertNotIn("Reply 20", [r["body"] for r in recent["replies"]])
        self.assertTrue(recent["hasMore"])
        older = self.client.get(f"/forum/topics/{topic}", params={"before": recent["replies"][0]["id"]}).json()
        self.assertEqual(len(older["replies"]), 4)
        self.assertFalse(older["hasMore"])


if __name__ == "__main__":
    unittest.main()
