import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.square import Square, PaymentUnavailable


class FakeProvider:
    name, mode, configured = "square", "sandbox", True
    is_paid = False

    def __init__(self):
        self.created = []

    def check_account(self):
        return True

    def create_checkout(self, order, return_url):
        self.created.append((copy.deepcopy(order), return_url))
        return "provider-order", "https://square.link/u/test"

    def paid(self, provider_id, amount):
        return self.is_paid


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.zip = self.root / "DESK-COMMANDER-X16.zip"
        self.zip.write_bytes(b"private release content")
        self.manifest = {"desk": {"file": self.zip.name, "sha256": hashlib.sha256(self.zip.read_bytes()).hexdigest(), "sandbox": True}}
        self.catalog = {"products": [{"id": "desk", "name": "Desk", "active": True,
                                     "status": "available", "type": "digital", "trackStock": False,
                                     "price": 3.99, "tags": []}]}
        self.provider = FakeProvider()
        self.database = self.root / "orders.sqlite3"
        self.client = self.make_client()

    def make_client(self, **kwargs):
        return TestClient(create_app(database=self.database, private_dir=self.root, manifest=self.manifest,
                                     provider=self.provider, catalog_loader=lambda: self.catalog,
                                     enabled=kwargs.get("enabled", True), site="https://roddy.world",
                                     public_url="https://api.example.test"))

    def checkout(self, **overrides):
        body = {"items": [{"id": "desk", "qty": 1}], "requestId": str(uuid4()), **overrides}
        return self.client.post("/checkout", json=body, headers={"origin": "https://roddy.world"})

    def status(self, session):
        return self.client.post("/order", json={"sessionId": session})

    def test_server_reprices_and_retry_reuses_provider_order(self):
        request_id = str(uuid4())
        first = self.checkout(requestId=request_id, amount=1, price=0.01)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(self.provider.created[0][0]["amount"], 399)
        self.assertIn("/order.html#session_id=", self.provider.created[0][1])
        self.catalog["products"][0]["price"] = 4.99
        retry = self.checkout(requestId=request_id)
        self.assertEqual(first.json(), retry.json())
        self.assertEqual(len(self.provider.created), 1)

    def test_disabled_checkout_and_foreign_origins_are_rejected(self):
        self.client = self.make_client(enabled=False)
        self.assertEqual(self.checkout().status_code, 503)
        self.client = self.make_client()
        self.assertEqual(self.client.post("/checkout", json={}, headers={"origin": "https://evil.test"}).status_code, 403)

    def test_unpaid_order_never_receives_download(self):
        session = self.checkout().json()["sessionId"]
        data = self.status(session).json()
        self.assertFalse(data["paid"])
        self.assertEqual(data["downloads"], [])
        self.assertEqual(self.client.get("/download/" + "a" * 43).status_code, 410)

    def test_paid_delivery_expires_and_refund_revokes_new_download(self):
        session = self.checkout().json()["sessionId"]
        self.provider.is_paid = True
        status = self.status(session)
        self.assertEqual(status.status_code, 200, status.text)
        url = status.json()["downloads"][0]["url"]
        path = url.removeprefix("https://api.example.test")
        response = self.client.get(path)
        self.assertEqual(response.content, self.zip.read_bytes())
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertIn("attachment", response.headers["content-disposition"])
        self.provider.is_paid = False
        self.assertEqual(self.client.get(path).status_code, 403)
        self.provider.is_paid = True
        with sqlite3.connect(self.database) as db:
            db.execute("UPDATE tickets SET expires=0")
        self.assertEqual(self.client.get(path).status_code, 410)
        fresh = self.status(session).json()["downloads"][0]["url"]
        self.assertNotEqual(url, fresh)

    def test_private_file_integrity_and_traversal_are_checked(self):
        self.manifest["desk"]["file"] = "../secret.zip"
        self.assertEqual(self.checkout().status_code, 503)
        self.manifest["desk"]["file"] = self.zip.name
        self.zip.write_bytes(b"wrong release")
        self.assertEqual(self.checkout().status_code, 503)
        self.assertEqual(self.client.get("/files/" + self.zip.name).status_code, 404)

    def test_sandbox_cannot_sell_a_live_release(self):
        self.manifest["desk"].pop("sandbox")
        self.assertEqual(self.checkout().status_code, 503)

    def test_unavailable_free_and_physical_products_are_rejected(self):
        original = copy.deepcopy(self.catalog["products"][0])
        for changes in [{"active": False}, {"status": "coming-soon"}, {"pricePending": True},
                        {"type": "physical"}, {"price": 0}, {"price": 3.991},
                        {"tags": ["free"]}, {"downloadUrl": "https://example.test/free.zip"}]:
            self.catalog["products"][0] = {**original, **changes}
            self.assertEqual(self.checkout().status_code, 409, changes)

    def test_bad_quantities_duplicates_unknown_products_and_request_ids(self):
        for items in [[{"id": "desk", "qty": 2}], [{"id": "desk", "qty": True}],
                      [{"id": "desk", "qty": 1}] * 2, [], [{"id": "missing", "qty": 1}]]:
            self.assertIn(self.checkout(items=items).status_code, (400, 409))
        self.assertEqual(self.checkout(requestId="guessable").status_code, 400)

    def test_idempotency_reference_cannot_be_reused_for_other_cart(self):
        request_id = str(uuid4())
        self.checkout(requestId=request_id)
        self.assertEqual(self.checkout(requestId=request_id, items=[{"id": "other", "qty": 1}]).status_code, 409)

    def test_unknown_and_expired_order_references_fail_closed(self):
        self.assertEqual(self.status("a" * 43).status_code, 404)
        session = self.checkout().json()["sessionId"]
        with sqlite3.connect(self.database) as db:
            db.execute("UPDATE orders SET created=0")
        self.assertEqual(self.status(session).status_code, 410)

    def test_provider_outage_does_not_create_paid_delivery(self):
        session = self.checkout().json()["sessionId"]
        with patch.object(self.provider, "paid", side_effect=PaymentUnavailable("Unavailable")):
            self.assertEqual(self.status(session).status_code, 503)
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute("SELECT paid FROM orders").fetchone()[0], 0)

    def test_provider_timeout_retry_keeps_same_receipt_and_idempotency_key(self):
        request_id = str(uuid4())
        with patch.object(self.provider, "create_checkout", side_effect=PaymentUnavailable("Unavailable")):
            self.assertEqual(self.checkout(requestId=request_id).status_code, 503)
        with sqlite3.connect(self.database) as db:
            session = db.execute("SELECT session FROM orders").fetchone()[0]
        retry = self.checkout(requestId=request_id)
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["sessionId"], session)
        self.assertEqual(self.provider.created[0][0]["request_id"], request_id)

    def test_untrusted_provider_redirect_is_rejected(self):
        with patch.object(self.provider, "create_checkout", return_value=("order", "https://square.link.evil.test/")):
            self.assertEqual(self.checkout().status_code, 503)

    def test_rate_limit_and_body_limit(self):
        for _ in range(10):
            self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/health").status_code, 429)
        self.assertEqual(self.client.post("/order", content="x" * 8193).status_code, 413)

    def test_admin_requires_owner_and_does_not_expose_download_secrets(self):
        self.checkout()
        self.assertEqual(self.client.get("/admin/orders").status_code, 401)
        response = type("Response", (), {"raise_for_status": lambda _: None, "json": lambda _: {"login": "someone"}})()
        with patch("backend.app.httpx.get", return_value=response):
            self.assertEqual(self.client.get("/admin/orders", headers={"authorization": "Bearer test"}).status_code, 403)
        response.json = lambda: {"login": "lionsarmor"}
        with patch("backend.app.httpx.get", return_value=response):
            result = self.client.get("/admin/orders", headers={"authorization": "Bearer test"})
        self.assertEqual(result.status_code, 200)
        for secret in ["session", "sha256", "file", "url"]:
            self.assertNotIn(secret, result.text)


class SquareTests(unittest.TestCase):
    def setUp(self):
        self.square = Square("test-token", "location")
        self.order = {"id": "order", "location_id": "location", "total_money": {"amount": 399, "currency": "USD"},
                      "tenders": [{"payment_id": "payment"}]}
        self.payment = {"order_id": "order", "location_id": "location", "status": "COMPLETED",
                        "amount_money": {"amount": 399, "currency": "USD"}}

    def verify(self):
        def response(method, path, body=None):
            return {"order": self.order} if "/orders/" in path else {"payment": self.payment}
        with patch.object(self.square, "request", side_effect=response):
            return self.square.paid("order", 399)

    def test_only_completed_correct_payment_is_paid(self):
        self.assertTrue(self.verify())
        original = copy.deepcopy(self.payment)
        for change in [{"status": "APPROVED"}, {"status": "PENDING"}, {"order_id": "different"},
                       {"location_id": "different"}, {"amount_money": {"amount": 1, "currency": "USD"}},
                       {"amount_money": {"amount": 399, "currency": "CAD"}},
                       {"refunded_money": {"amount": 1}}, {"refund_ids": ["pending-refund"]}]:
            self.payment = {**original, **change}
            self.assertFalse(self.verify(), change)

    def test_wrong_order_location_total_and_cancellation_fail(self):
        original = copy.deepcopy(self.order)
        for change in [{"id": "different"}, {"location_id": "different"}, {"state": "CANCELED"},
                       {"tenders": []}, {"total_money": {"amount": 398, "currency": "USD"}}]:
            self.order = {**original, **change}
            self.assertFalse(self.verify(), change)

    def test_create_link_uses_idempotency_server_total_and_return_url(self):
        with patch.object(self.square, "request", return_value={"payment_link": {"order_id": "order", "url": "https://square.link/u/example"}}) as request:
            self.square.create_checkout({"request_id": "request", "items": [{"name": "Desk"}], "amount": 399}, "https://roddy.world/order.html#session_id=secret")
        payload = request.call_args.args[2]
        self.assertEqual(payload["idempotency_key"], "request")
        self.assertEqual(payload["quick_pay"]["price_money"], {"amount": 399, "currency": "USD"})
        self.assertFalse(payload["checkout_options"]["ask_for_shipping_address"])
        self.assertFalse(payload["checkout_options"]["enable_tipping"])

    def test_quick_pay_tender_id_is_supported_without_payment_id(self):
        self.order["tenders"] = [{"id": "payment"}]
        self.assertTrue(self.verify())


if __name__ == "__main__":
    unittest.main()
