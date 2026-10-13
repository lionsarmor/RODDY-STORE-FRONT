import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.test_checkout import FakeProvider

CONTENT = {"title": "April news", "subject": "Something new & strange", "preheader": "A little signal",
           "palette": "confetti", "blocks": [{"kind": "offer", "heading": "A good offer", "body": "Two lines\nof news",
           "image": "https://roddy.world/img/hoodie.jpg", "alt": "Our hoodie", "badge": "NEW", "price": "$35.99 + shipping",
           "link": "https://roddy.world/#/product/hoodie", "button": "Shop hoodies"}]}


class NewsletterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / "store.sqlite3"
        self.client = TestClient(self.make_app())
        self.origin = {"origin": "https://roddy.world"}

    def make_app(self):
        return create_app(database=self.database, private_dir=self.root, manifest={}, provider=FakeProvider(),
                          catalog_loader=lambda: {"products": []}, enabled=False, worker_enabled=False)

    def admin(self, method, path="", body=None, login="lionsarmor"):
        response = type("Response", (), {"raise_for_status": lambda _: None, "json": lambda _: {"login": login}})()
        with patch("backend.app.httpx.get", return_value=response):
            return self.client.request(method, "/admin/newsletters" + path, json=body, headers={"authorization": "Bearer owner-test"})

    def signup(self, email="maker@example.com", **extra):
        return self.client.post("/newsletter/subscribe", headers=self.origin, json={"email": email, "consent": True, **extra})

    def draft(self):
        result = self.admin("POST", "/drafts", {"content": CONTENT})
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()["campaign"]

    def test_explicit_optin_deduplicates_persists_and_is_not_public(self):
        self.assertEqual(self.signup(" Maker@Example.com ").status_code, 200)
        self.assertEqual(self.signup().status_code, 200)
        overview = self.admin("GET").json()
        self.assertEqual(overview["counts"], {"active": 1})
        self.client = TestClient(self.make_app())
        row = self.admin("GET", "/subscribers").json()["subscribers"][0]
        self.assertEqual(row["email"], "maker@example.com")
        self.assertIn("occasional RODDY", row["consent"])
        for path in ["", "/subscribers", "/subscribers.csv"]:
            self.assertEqual(self.client.get("/admin/newsletters" + path).status_code, 401)
        self.assertEqual(self.admin("GET", login="someone-else").status_code, 403)
        self.assertNotIn("maker@example.com", self.signup().text)

    def test_origin_consent_honeypot_invalid_input_and_throttle(self):
        body = {"email": "maker@example.com", "consent": True}
        self.assertEqual(self.client.post("/newsletter/subscribe", json=body).status_code, 403)
        self.assertEqual(self.signup(consent=False).status_code, 400)
        self.assertEqual(self.signup("maker@example.com\r\nBcc:other@example.com").status_code, 400)
        self.assertEqual(self.signup(company="bot").status_code, 200)
        self.assertEqual(self.signup().status_code, 429)
        self.assertEqual(self.admin("GET").json()["counts"], {})

    def test_suppression_excludes_repeated_signup_and_future_export(self):
        self.signup()
        self.admin("POST", "/subscribers/unsubscribe", {"email": "MAKER@example.com"})
        self.signup()
        self.assertEqual(self.admin("GET").json()["counts"], {"unsubscribed": 1})
        draft = self.draft()
        self.admin("POST", "/settings", {"postalAddress": "Example Business, PO Box 123, Example, WY 12345, US"})
        data = self.admin("POST", "/prepare", {"id": draft["id"], "revision": 1}).json()
        self.assertEqual(data["batches"], [])
        self.assertEqual(data["count"], 0)
        self.assertIn("mailto:roddy2020@protonmail.com", data["html"])
        self.assertIn("unsubscribe", data["text"])

    def test_revision_conflicts_leave_original_draft_intact_and_copy_works(self):
        draft = self.draft()
        content = copy.deepcopy(CONTENT); content["subject"] = "Changed in another browser"
        updated = self.admin("POST", "/drafts", {"id": draft["id"], "revision": 1, "content": content})
        self.assertEqual(updated.json()["campaign"]["revision"], 2)
        conflict = self.admin("POST", "/drafts", {"id": draft["id"], "revision": 1, "content": CONTENT})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(self.admin("GET").json()["campaigns"][0]["content"]["subject"], content["subject"])
        self.assertNotEqual(self.draft()["id"], draft["id"])

    def test_render_escapes_html_and_rejects_dangerous_links(self):
        content = copy.deepcopy(CONTENT)
        content["blocks"][0]["heading"] = '<script>alert("x")</script>'
        result = self.admin("POST", "/preview", {"content": content}).json()
        self.assertIn("&lt;script&gt;", result["html"])
        self.assertNotIn("<script>", result["html"])
        self.assertIn("[Add your business mailing address", result["text"])
        for invalid in ["javascript:alert(1)", "data:image/png;base64,AA", "https://[invalid", "https://a:b@roddy.world", "http://example.com"]:
            content["blocks"][0]["image"] = invalid
            self.assertEqual(self.admin("POST", "/preview", {"content": content}).status_code, 400)

    def test_manual_prepare_footer_batches_freshness_and_recording(self):
        draft = self.draft()
        key = {"id": draft["id"], "revision": draft["revision"]}
        self.assertEqual(self.admin("POST", "/prepare", key).status_code, 409)
        self.admin("POST", "/settings", {"postalAddress": "Test Business, PO Box 123, Example, WY 12345, US"})
        with sqlite3.connect(self.database) as db:
            db.executemany("INSERT INTO newsletter_subscribers(email,created,updated,consent,source) VALUES(?,1,1,'explicit test consent','test')", [(f"maker{n}@example.com",) for n in range(101)])
        result = self.admin("POST", "/prepare", key).json()
        self.assertEqual([len(batch.split(", ")) for batch in result["batches"]], [50, 50, 1])
        self.assertEqual(result["count"], 101)
        self.assertIn("Test Business", result["html"])
        self.admin("POST", "/subscribers/unsubscribe", {"email": "maker0@example.com"})
        sent = {**key, "audienceHash": result["audienceHash"], "confirmedManualSend": True}
        self.assertEqual(self.admin("POST", "/record-sent", sent).status_code, 409)
        fresh = self.admin("POST", "/prepare", key).json()
        self.assertEqual(fresh["count"], 100)
        self.assertNotIn("maker0@example.com", ", ".join(fresh["batches"]))
        sent["audienceHash"] = fresh["audienceHash"]
        self.assertEqual(self.admin("POST", "/record-sent", {**sent, "confirmedManualSend": False}).status_code, 400)
        self.assertEqual(self.admin("POST", "/record-sent", sent).status_code, 200)
        self.assertEqual(self.admin("POST", "/record-sent", sent).status_code, 200)
        stored = self.admin("GET").json()["campaigns"][0]
        self.assertEqual(stored["sentCount"], 100)
        self.assertIsNotNone(stored["sentAt"])
        self.assertEqual(self.admin("POST", "/drafts", {**key, "content": CONTENT}).status_code, 409)

    def test_csv_formula_escaping_and_paging(self):
        self.signup("+formula@example.com")
        csv = self.admin("GET", "/subscribers.csv")
        self.assertEqual(csv.status_code, 200)
        self.assertIn("'+formula@example.com", csv.text)
        self.assertIn("attachment", csv.headers["content-disposition"])
        self.assertEqual(self.admin("GET", "/subscribers?page=0").status_code, 400)
        self.assertEqual(self.admin("GET", "/subscribers?search=formula").json()["subscribers"][0]["email"], "+formula@example.com")

    def test_long_newsletter_copy_keeps_other_endpoint_body_limits(self):
        content = copy.deepcopy(CONTENT)
        content["blocks"] = [{**content["blocks"][0], "body": "x" * 2000} for _ in range(5)]
        self.assertGreater(len(json.dumps(content)), 8192)
        self.assertEqual(self.admin("POST", "/drafts", {"content": content}).status_code, 200)
        self.assertEqual(self.signup(company="x" * 9000).status_code, 413)
        self.assertEqual(self.admin("POST", "/preview", {"content": {**content, "padding": "x" * 66000}}).status_code, 413)


if __name__ == "__main__":
    unittest.main()
