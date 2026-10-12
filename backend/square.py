"""Square-hosted checkout. Card details never pass through this server."""

import httpx


class PaymentUnavailable(Exception):
    pass


class Square:
    name = "square"

    def __init__(self, token, location, mode="sandbox"):
        if mode not in {"sandbox", "live"}:
            raise ValueError("SQUARE_MODE must be sandbox or live")
        self.token, self.location, self.mode = token, location, mode
        self.base = ("https://connect.squareup.com" if mode == "live"
                     else "https://connect.squareupsandbox.com")

    @property
    def configured(self):
        return bool(self.token and self.location)

    def request(self, method, path, body=None):
        try:
            response = httpx.request(
                method, self.base + path, json=body, timeout=20,
                headers={"Authorization": "Bearer " + self.token,
                         "Square-Version": "2026-09-16"},
            )
            response.raise_for_status()
            data = response.json()
            if data.get("errors"):
                raise ValueError("Square returned errors")
            return data
        except (httpx.HTTPError, ValueError) as exc:
            # Provider response bodies can contain customer details. Do not echo them.
            raise PaymentUnavailable("Payment service is unavailable. Please try again.") from exc

    def check_account(self):
        location = self.request("GET", "/v2/locations/" + self.location)["location"]
        return (location.get("status") == "ACTIVE" and location.get("currency") == "USD"
                and "CREDIT_CARD_PROCESSING" in location.get("capabilities", []))

    def create_checkout(self, order, return_url):
        data = self.request("POST", "/v2/online-checkout/payment-links", {
            "idempotency_key": order["request_id"],
            "quick_pay": {
                "name": " + ".join(item["name"] for item in order["items"]),
                "location_id": self.location,
                "price_money": {"amount": order["amount"], "currency": "USD"},
            },
            "checkout_options": {
                "redirect_url": return_url,
                "ask_for_shipping_address": False,
                "enable_tipping": False,
            },
        })["payment_link"]
        return data["order_id"], data["url"]

    def paid(self, provider_id, amount):
        order = self.request("GET", "/v2/orders/" + provider_id)["order"]
        expected = {"amount": amount, "currency": "USD"}
        if (order.get("id") != provider_id or order.get("location_id") != self.location
                or order.get("total_money") != expected or order.get("state") == "CANCELED"):
            return False
        # A successful redirect or an order's status alone is not proof of payment.
        for tender in order.get("tenders", []):
            payment_id = tender.get("payment_id") or tender.get("id")
            if not payment_id:
                continue
            payment = self.request("GET", "/v2/payments/" + payment_id)["payment"]
            if (payment.get("order_id") == provider_id
                    and payment.get("location_id") == self.location
                    and payment.get("status") == "COMPLETED"
                    and payment.get("amount_money") == expected
                    and not payment.get("refund_ids")
                    and payment.get("refunded_money", {}).get("amount", 0) == 0):
                return True
        return False
