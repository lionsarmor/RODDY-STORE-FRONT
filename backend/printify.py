"""Read-only Printify product, variant and standard shipping discovery."""
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class PrintifyUnavailable(Exception):
    pass


def image_url(value):
    if not isinstance(value, str):
        return ""
    try:
        url = urlsplit(value)
        return value if url.scheme == "https" and url.hostname and not url.username and not url.password else ""
    except ValueError:
        return ""


def product_summary(product):
    options = [{"name": o.get("name", "Option"), "type": o.get("type", "other"),
                "values": [{"id": v["id"], "title": v.get("title", str(v["id"])),
                            "colors": [c for c in v.get("colors", []) if isinstance(c, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", c)]}
                           for v in o.get("values", [])]}
               for o in product.get("options", [])]
    values = {v["id"]: (o["type"], v) for o in options for v in o["values"]}
    variants = []
    for v in product.get("variants", []):
        selected = {values[i][0]: values[i][1] for i in v.get("options", []) if i in values}
        variants.append({"id": v["id"], "title": v.get("title", str(v["id"])),
                         "size": selected.get("size", {}).get("title", ""),
                         "color": selected.get("color", {}).get("title", ""),
                         "colors": selected.get("color", {}).get("colors", []),
                         "sku": v.get("sku", ""),
                         "enabled": v.get("is_enabled") is True,
                         "available": v.get("is_available") if type(v.get("is_available")) is bool else None,
                         "priceCents": v.get("price"), "costCents": v.get("cost")})
    return {"id": product["id"], "title": product.get("title", "Product"),
            "blueprintId": product.get("blueprint_id"), "printProviderId": product.get("print_provider_id"),
            "options": options, "variants": variants,
            "images": [{"src": image_url(i.get("src")), "variantIds": i.get("variant_ids", [])}
                       for i in product.get("images", []) if image_url(i.get("src"))]}


class Printify:
    def __init__(self, token, shop_id=None):
        self.token = token
        self.shop_id = shop_id

    def get(self, path, version="v1"):
        if version not in {"v1", "v2"}:
            raise PrintifyUnavailable("Invalid Printify API version.")
        request = Request(f"https://api.printify.com/{version}/" + path, headers={
            "Authorization": "Bearer " + self.token,
            "User-Agent": "RODDY-Store/1.0", "Accept": "application/json",
        })
        try:
            with urlopen(request, timeout=20) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code == 401:
                message = "Printify rejected the token. Generate a new token in Printify Connections."
            elif exc.code == 403:
                message = "Printify denied access. Check shops.read, products.read and catalog.read token permissions."
            elif exc.code == 429:
                message = "Printify rate limit reached. Try again shortly."
            else:
                message = f"Printify returned HTTP {exc.code}. Try again later."
            raise PrintifyUnavailable(message) from None
        except (URLError, TimeoutError, ValueError):
            raise PrintifyUnavailable("Could not read a response from Printify. Try again later.") from None

    def shops(self):
        shops = self.get("shops.json")
        if not isinstance(shops, list):
            raise PrintifyUnavailable("Printify returned an invalid shop list.")
        return [{"id": s["id"], "title": s.get("title", "Store"),
                 "channel": s.get("sales_channel", "unknown")}
                for s in shops if isinstance(s, dict) and type(s.get("id")) is int]

    def check_shop(self):
        if type(self.shop_id) is not int or self.shop_id < 1:
            raise PrintifyUnavailable("Choose a Printify store using the droplet setup command.")

    def products(self, page=1):
        self.check_shop()
        if type(page) is not int or not 1 <= page <= 10000:
            raise PrintifyUnavailable("Invalid product page.")
        data = self.get(f"shops/{self.shop_id}/products.json?page={page}&limit=50")
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise PrintifyUnavailable("Printify returned an invalid product list.")
        return {"products": [product_summary(p) for p in data["data"]], "page": page,
                "hasMore": bool(data.get("next_page_url"))}

    def product(self, product_id):
        self.check_shop()
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", product_id):
            raise PrintifyUnavailable("Invalid Printify product ID.")
        data = self.get(f"shops/{self.shop_id}/products/{product_id}.json")
        if not isinstance(data, dict) or data.get("id") != product_id:
            raise PrintifyUnavailable("Printify returned an invalid product.")
        product = product_summary(data)
        # Missing catalog permission must never turn a missing shipping rate into
        # free shipping. Product import can proceed with an explicit warning.
        try:
            product["shippingProfiles"] = self.shipping(product["blueprintId"], product["printProviderId"])
            product["shippingWarning"] = ""
        except PrintifyUnavailable as exc:
            product["shippingProfiles"] = []
            product["shippingWarning"] = str(exc)
        return product

    def shipping(self, blueprint, provider):
        if any(type(i) is not int or i < 1 for i in [blueprint, provider]):
            raise PrintifyUnavailable("This product has no valid print provider.")
        data = self.get(f"catalog/blueprints/{blueprint}/print_providers/{provider}/shipping/standard.json", version="v2")
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise PrintifyUnavailable("Printify did not return standard shipping rates.")
        profiles = {}
        for row in data["data"]:
            p = row.get("attributes", {})
            cost = p.get("shippingCost", {})
            first, additional = cost.get("firstItem", {}), cost.get("additionalItems", {})
            country = p.get("country", {}).get("code", "")
            variant = p.get("variantId")
            if (p.get("shippingType") != "standard" or first.get("currency") != "USD" or additional.get("currency") != "USD"
                    or type(variant) is not int or variant < 1
                    or not isinstance(country, str)
                    or not (re.fullmatch(r"[A-Z]{2}", country) or country == "REST_OF_THE_WORLD")
                    or any(type(i) is not int or i < 0 for i in [first.get("amount"), additional.get("amount")])):
                continue
            key = (country, first["amount"], additional["amount"])
            profile = profiles.setdefault(key, {"variantIds": [], "countries": [country],
                                              "firstItem": first["amount"] / 100,
                                              "additionalItem": additional["amount"] / 100})
            if variant not in profile["variantIds"]:
                profile["variantIds"].append(variant)
        return list(profiles.values())


def load_connection(path="/etc/roddy-store/printify.json"):
    try:
        config = json.loads(Path(path).read_text())
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        raise PrintifyUnavailable("Could not read Printify configuration. Run the droplet setup command again.") from None
    if (not isinstance(config, dict) or not isinstance(config.get("token"), str)
            or not config["token"] or type(config.get("shopId")) is not int or config["shopId"] < 1):
        raise PrintifyUnavailable("Printify configuration is incomplete. Run the droplet setup command again.")
    return Printify(config["token"], config["shopId"])
