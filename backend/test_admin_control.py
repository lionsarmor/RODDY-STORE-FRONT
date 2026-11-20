import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.admin_control import COOKIE, SESSION_SECONDS, register_admin_control


ORIGIN = "https://store.example.test"


class AdminControlTests(TestCase):
    def test_owner_gate_protects_page_and_assets_until_sign_out(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "assets").mkdir()
            (root / "assets/private.js").write_text("private bundle")
            (root / "admin.html").write_text("private dashboard")
            app = FastAPI()

            def verify_owner(request, token):
                if token != "Bearer test-owner-token":
                    raise HTTPException(401)

            with patch.dict(os.environ, {"STORE_ADMIN_DIR": temp}):
                register_admin_control(app, verify_owner, ORIGIN)

            client = TestClient(app, base_url=ORIGIN, follow_redirects=False)
            login = client.get("/control/")
            self.assertIn("GitHub token", login.text)
            self.assertNotIn("private dashboard", login.text)
            self.assertEqual(login.headers["cache-control"], "no-store")
            self.assertEqual(client.get("/control/assets/private.js").status_code, 401)

            other_origin = client.post("/control/session", data={"token": "test-owner-token"},
                                       headers={"Origin": "https://different.example.test"})
            self.assertEqual(other_origin.status_code, 403)
            headers = {"Origin": ORIGIN}
            denied = client.post("/control/session", data={"token": "invalid"}, headers=headers)
            self.assertEqual(denied.status_code, 401)
            unlock = client.post("/control/session",
                                 data={"token": "test-owner-token", "fragment": "#workshop"}, headers=headers)
            self.assertEqual(unlock.status_code, 303)
            self.assertEqual(unlock.headers["location"], "/control/#workshop")
            cookie = unlock.headers["set-cookie"]
            for attr in ("HttpOnly", "Secure", "SameSite=strict", f"Max-Age={SESSION_SECONDS}"):
                self.assertIn(attr, cookie)
            self.assertNotIn("test-owner-token", str(unlock.headers))
            self.assertEqual(client.get("/control/").text, "private dashboard")
            self.assertEqual(client.get("/control/assets/private.js").text, "private bundle")
            self.assertEqual(client.get("/control/assets/%2e%2e/admin.html").status_code, 404)

            saved_session = client.cookies[COOKIE]
            client.post("/control/logout", headers=headers)
            client.cookies.set(COOKIE, saved_session, path="/control/")
            self.assertEqual(client.get("/control/assets/private.js").status_code, 401)

    def test_expired_session_does_not_read_admin_html(self):
        app = FastAPI()
        register_admin_control(app, lambda request, token: None, ORIGIN)
        client = TestClient(app, base_url=ORIGIN)
        with patch("backend.admin_control.time.monotonic", return_value=100):
            client.post("/control/session", data={"token": "test-owner-token"}, headers={"Origin": ORIGIN})
        with patch("backend.admin_control.time.monotonic", return_value=100 + SESSION_SECONDS):
            self.assertIn("GitHub token", client.get("/control/").text)
