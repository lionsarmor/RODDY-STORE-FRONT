"""Read-only Printify account setup and product discovery. No production orders."""
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class PrintifyUnavailable(Exception):
    pass


class Printify:
    def __init__(self, token, shop_id=None):
        self.token = token
        self.shop_id = shop_id

    def get(self, path):
        request = Request("https://api.printify.com/v1/" + path, headers={
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
                message = "Printify denied access. Check the token's shops.read and products.read permissions."
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

    def products(self, page=1):
        if type(self.shop_id) is not int or self.shop_id < 1:
            raise PrintifyUnavailable("Choose a Printify store using the droplet setup command.")
        if type(page) is not int or not 1 <= page <= 10000:
            raise PrintifyUnavailable("Invalid product page.")
        data = self.get(f"shops/{self.shop_id}/products.json?page={page}&limit=50")
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise PrintifyUnavailable("Printify returned an invalid product list.")
        products = []
        for product in data["data"]:
            # Deliberately whitelist fields: no artwork URLs or arbitrary provider
            # response data are exposed through the storefront admin API.
            products.append({"id": product["id"], "title": product.get("title", "Product"),
                "blueprintId": product.get("blueprint_id"),
                "printProviderId": product.get("print_provider_id"),
                "variants": [{"id": v["id"], "title": v.get("title", str(v["id"])),
                              "enabled": v.get("is_enabled") is True,
                              "available": v.get("is_available"),
                              "priceCents": v.get("price"), "costCents": v.get("cost")}
                             for v in product.get("variants", [])]})
        return {"products": products, "page": page,
                "hasMore": bool(data.get("next_page_url"))}


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
