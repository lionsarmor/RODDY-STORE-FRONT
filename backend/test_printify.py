import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from fastapi.testclient import TestClient
from backend.app import create_app
from backend.printify import Printify, PrintifyUnavailable, load_connection


class PrintifyTests(unittest.TestCase):
    def test_discovery_is_read_only_and_never_follows_pagination_urls(self):
        data = {"data": [{"id": "hoodie", "title": "RODDY Hoodie", "private_extra": "hidden",
                         "variants": [{"id": 123, "title": "Black / XL", "is_enabled": True,
                                       "is_available": False, "price": 4500, "cost": 2000}]}],
                "next_page_url": "https://untrusted.invalid/?token=hidden"}
        response = io.StringIO(json.dumps(data))
        with patch("backend.printify.urlopen", return_value=response) as request:
            result = Printify("private-token", 123).products(2)
        sent = request.call_args.args[0]
        self.assertEqual(sent.get_method(), "GET")
        self.assertEqual(sent.full_url, "https://api.printify.com/v1/shops/123/products.json?page=2&limit=50")
        self.assertEqual(sent.get_header("User-agent"), "RODDY-Store/1.0")
        self.assertTrue(result["hasMore"])
        self.assertEqual(result["products"][0]["variants"][0]["title"], "Black / XL")
        self.assertFalse(result["products"][0]["variants"][0]["available"])
        self.assertNotIn("hidden", json.dumps(result))
        self.assertNotIn("private-token", json.dumps(result))

    def test_product_options_use_option_ids_not_title_parsing_and_preserve_stock(self):
        data = {"data": [{"id": "hoodie", "options": [
            {"type": "color", "values": [{"id": 418, "title": "Black", "colors": ["#000000", "url(secret)"]}]},
            {"type": "size", "values": [{"id": 14, "title": "S"}]}],
            "variants": [{"id": 1, "title": "Any title", "options": [418,14], "is_enabled": True,
                          "is_available": False, "price": 3596, "cost": 2158}],
            "images": [{"src": "javascript:alert(1)", "variant_ids": [1]},
                       {"src": "https://images.example/mat.png", "variant_ids": [1]}]}]}
        with patch.object(Printify, "get", return_value=data):
            p = Printify("private-token",123).products()["products"][0]
        self.assertEqual(p["variants"][0]["color"], "Black")
        self.assertEqual(p["variants"][0]["size"], "S")
        self.assertEqual(p["variants"][0]["colors"], ["#000000"])
        self.assertFalse(p["variants"][0]["available"])
        self.assertEqual(len(p["images"]),1)

    def test_standard_shipping_uses_v2_and_only_accepts_usd_valid_rates(self):
        def row(variant, country, amount, currency="USD", shipping_type="standard"):
            return {"attributes": {"variantId": variant, "country": {"code": country}, "shippingType": shipping_type,
                "shippingCost": {"firstItem": {"amount": amount, "currency": currency},
                                 "additionalItems": {"amount": 209, "currency": currency}}}}
        data={"data":[row(1,"US",879),row(2,"US",879),row(1,"CA",1319),
                      row(1,"US",300,"CAD"),row(3,"US",-1),row(4,"US",739,shipping_type="economy")]}
        with patch.object(Printify,"get",return_value=data) as get:
            rates=Printify("private-token",123).shipping(77,99)
        get.assert_called_once_with("catalog/blueprints/77/print_providers/99/shipping/standard.json",version="v2")
        self.assertEqual(rates,[{"variantIds":[1,2],"countries":["US"],"firstItem":8.79,"additionalItem":2.09},
                                {"variantIds":[1],"countries":["CA"],"firstItem":13.19,"additionalItem":2.09}])

    def test_shipping_permission_failure_keeps_product_import_and_reports_missing_rates(self):
        with patch.object(Printify,"get",return_value={"id":"hoodie"}), \
             patch.object(Printify,"shipping",side_effect=PrintifyUnavailable("Shipping denied")):
            result=Printify("private-token",123).product("hoodie")
        self.assertEqual(result["shippingProfiles"],[])
        self.assertEqual(result["shippingWarning"],"Shipping denied")
        with self.assertRaises(PrintifyUnavailable):
            Printify("private-token",123).product("../shops")

    def test_product_detail_requires_admin_and_never_returns_the_token(self):
        with tempfile.TemporaryDirectory() as temp:
            client=TestClient(create_app(database=Path(temp)/"orders.sqlite3"))
            with patch("backend.app.load_connection") as load:
                self.assertEqual(client.get("/admin/printify/products/hoodie").status_code,401)
                load.assert_not_called()
            user=Mock();user.json.return_value={"login":"lionsarmor"}
            provider=Mock(shop_id=123)
            provider.product.return_value={"id":"hoodie","shippingProfiles":[]}
            with patch("backend.app.httpx.get",return_value=user), patch("backend.app.load_connection",return_value=provider):
                response=client.get("/admin/printify/products/hoodie",headers={"authorization":"Bearer private-github-token"})
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.json()["shopId"],123)
                self.assertNotIn("private-github-token",response.text)
                provider.product.assert_called_once_with("hoodie")

    def test_provider_errors_do_not_expose_tokens_or_response_bodies(self):
        for status in [401, 403, 429, 500]:
            with self.subTest(status=status), patch("backend.printify.urlopen", side_effect=HTTPError(
                    "https://api.printify.com", status, "private-token", {}, io.BytesIO(b"private-token"))):
                with self.assertRaises(PrintifyUnavailable) as caught:
                    Printify("private-token").shops()
                self.assertNotIn("private-token", str(caught.exception))

    def test_configuration_is_optional_and_invalid_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "printify.json"
            self.assertIsNone(load_connection(path))
            path.write_text('{"token":"secret", "shopId":"not-an-integer"}')
            with self.assertRaises(PrintifyUnavailable):
                load_connection(path)
            path.write_text('{"token":"secret", "shopId":123}')
            self.assertEqual(load_connection(path).shop_id, 123)

    def test_admin_auth_is_required_before_reading_printify_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            client = TestClient(create_app(database=Path(temp) / "orders.sqlite3"))
            with patch("backend.app.load_connection") as load:
                self.assertEqual(client.get("/admin/printify").status_code, 401)
                user = Mock(); user.json.return_value = {"login": "someone-else"}
                with patch("backend.app.httpx.get", return_value=user):
                    response = client.get("/admin/printify", headers={"authorization": "Bearer test"})
                    self.assertEqual(response.status_code, 403)
                load.assert_not_called()

    def test_admin_reports_connection_and_variants_without_enabling_fulfillment(self):
        with tempfile.TemporaryDirectory() as temp:
            client = TestClient(create_app(database=Path(temp) / "orders.sqlite3"))
            user = Mock(); user.json.return_value = {"login": "lionsarmor"}
            headers = {"authorization": "Bearer test"}
            with patch("backend.app.httpx.get", return_value=user), patch("backend.app.load_connection", return_value=None):
                response = client.get("/admin/printify", headers=headers)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.json()["configured"])
            provider = Mock(shop_id=123)
            provider.shops.return_value = [{"id": 123, "title": "RODDY", "channel": "api"}]
            provider.products.return_value = {"products": [{"id": "hoodie", "variants": []}], "page": 1, "hasMore": False}
            with patch("backend.app.httpx.get", return_value=user), patch("backend.app.load_connection", return_value=provider):
                response = client.get("/admin/printify", headers=headers)
                self.assertTrue(response.json()["configured"])
                self.assertFalse(response.json()["fulfillmentEnabled"])
                self.assertEqual(response.json()["shop"]["title"], "RODDY")
                self.assertEqual(client.get("/admin/printify?page=0", headers=headers).status_code, 400)

    def test_failed_setup_preserves_existing_credentials(self):
        spec = importlib.util.spec_from_file_location("configure_printify", Path(__file__).parent / "deploy/configure-printify.py")
        setup = importlib.util.module_from_spec(spec); spec.loader.exec_module(setup)
        output = io.StringIO()
        with patch("sys.argv", ["configure-printify.py"]), patch.object(setup.os, "geteuid", return_value=0), \
             patch.object(setup.getpass, "getpass", return_value="private-test-token-should-not-display"), \
             patch.object(setup.Printify, "shops", side_effect=PrintifyUnavailable("Printify rejected the token.")), \
             patch.object(setup, "save_connection") as save, contextlib.redirect_stderr(output):
            with self.assertRaises(SystemExit):
                setup.main()
            save.assert_not_called()
            self.assertIn("Nothing saved", output.getvalue())
            self.assertNotIn("private-test-token", output.getvalue())

    def test_successful_setup_checks_product_permission_and_saves_selected_shop(self):
        spec = importlib.util.spec_from_file_location("configure_printify", Path(__file__).parent / "deploy/configure-printify.py")
        setup = importlib.util.module_from_spec(spec); spec.loader.exec_module(setup)
        output = io.StringIO()
        with patch("sys.argv", ["configure-printify.py"]), patch.object(setup.os, "geteuid", return_value=0), \
             patch.object(setup.getpass, "getpass", return_value="private-test-token-should-not-display"), \
             patch.object(setup.Printify, "shops", return_value=[{"id": 123, "title": "RODDY", "channel": "api"}]), \
             patch.object(setup.Printify, "products", return_value={"products": []}) as products, \
             patch.object(setup, "save_connection") as save, contextlib.redirect_stdout(output):
            setup.main()
            products.assert_called_once()
            self.assertEqual(save.call_args.args[1]["shopId"], 123)
            self.assertIn("Connected Printify store", output.getvalue())
            self.assertNotIn("private-test-token", output.getvalue())


if __name__ == "__main__":
    unittest.main()
