"""Square-hosted checkout. Card details never pass through this server."""

import httpx


class PaymentUnavailable(Exception):
    pass


class PaymentInputError(PaymentUnavailable):
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
            data = response.json()
            if response.status_code == 400 and any(e.get("code") == "INVALID_EMAIL_ADDRESS" for e in data.get("errors", [])):
                raise PaymentInputError("Square could not accept that email address. Check it and calculate shipping again.")
            response.raise_for_status()
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
        address = order.get("address")
        options = {"redirect_url": return_url, "ask_for_shipping_address": False,
                   "enable_tipping": False, "enable_coupon": False, "enable_loyalty": False}
        payload = {"idempotency_key": order["request_id"], "checkout_options": options}
        if order.get("quote_id"):
            payload["order"] = {"location_id": self.location, "reference_id": order["request_id"],
                "line_items": [{"name": (i["name"] + (" — " + i["label"] if i.get("label") else ""))[:500],
                                "quantity": str(i.get("qty", 1)),
                                "base_price_money": {"amount": i["cents"], "currency": "USD"}} for i in order["items"]]}
            if order.get("shipping"):
                # checkout_options.shipping_fee requires a second, editable
                # shipping address. Keep RODDY's quoted address fixed instead.
                payload["order"]["service_charges"] = [{"name": "Standard shipping",
                    "amount_money": {"amount": order["shipping"], "currency": "USD"},
                    "calculation_phase": "SUBTOTAL_PHASE", "taxable": False}]
            if address:
                payload["pre_populated_data"] = {"buyer_email": address["email"]}
                # Address is already validated/quoted on RODDY and stays fixed.
                payload["payment_note"] = "Delivery address and order tracking: " + return_url
        else:
            payload["quick_pay"] = {"name": " + ".join(i["name"] for i in order["items"]),
                "location_id": self.location, "price_money": {"amount": order["amount"], "currency": "USD"}}
        link = self.request("POST", "/v2/online-checkout/payment-links", payload)["payment_link"]
        return link["order_id"], link["url"], link.get("id")

    def cancel_checkout(self, link_id):
        if not isinstance(link_id, str) or not link_id.isalnum():
            raise PaymentUnavailable("Invalid payment link reference.")
        return self.request("DELETE", "/v2/online-checkout/payment-links/" + link_id)

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
