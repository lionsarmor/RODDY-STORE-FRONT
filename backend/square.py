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

    def payment_report(self, provider_id, amount):
        order = self.request("GET", "/v2/orders/" + provider_id)["order"]
        expected = {"amount": amount, "currency": "USD"}
        report = {"fullyPaid": False, "status": "unconfirmed", "captured": 0,
                  "refunded": 0, "fees": None, "tax": None, "paidAt": None, "payments": []}
        if (order.get("id") != provider_id or order.get("location_id") != self.location
                or order.get("total_money") != expected):
            return report
        report["tax"] = order.get("total_tax_money", {}).get("amount")
        fees, fees_known, refund_pending = 0, True, False
        for tender in order.get("tenders", []):
            payment_id = tender.get("payment_id") or tender.get("id")
            if not payment_id:
                continue
            payment = self.request("GET", "/v2/payments/" + payment_id)["payment"]
            money = payment.get("amount_money", {})
            if (payment.get("order_id") != provider_id or payment.get("location_id") != self.location
                    or money.get("currency") != "USD" or type(money.get("amount")) is not int):
                continue
            refunded = payment.get("refunded_money", {}).get("amount", 0)
            known_fee = payment.get("processing_fee")
            receipt = {"id": payment_id, "status": payment.get("status"), "amount": money["amount"],
                       "refunded": refunded, "createdAt": payment.get("created_at"),
                       "refundIds": payment.get("refund_ids", [])}
            report["payments"].append(receipt)
            if payment.get("status") == "COMPLETED":
                report["captured"] += money["amount"]
                report["refunded"] += refunded
                if payment.get("created_at"):
                    report["paidAt"] = min(report["paidAt"] or payment["created_at"], payment["created_at"])
                fees_known = fees_known and isinstance(known_fee, list)
                fees += sum(f.get("amount_money", {}).get("amount", 0) for f in known_fee or [])
                refund_pending = refund_pending or bool(payment.get("refund_ids") and not refunded)
        report["fees"] = fees if fees_known and report["captured"] else None
        report["fullyPaid"] = (report["captured"] == amount and not report["refunded"]
                               and not refund_pending and order.get("state") != "CANCELED")
        report["status"] = ("refunded" if report["captured"] and report["refunded"] >= report["captured"]
                            else "partially-refunded" if report["refunded"]
                            else "payment-review" if refund_pending
                            else "paid" if report["fullyPaid"]
                            else "canceled" if order.get("state") == "CANCELED"
                            else "processing" if any(p["status"] in {"APPROVED", "PENDING"} for p in report["payments"])
                            else "failed" if any(p["status"] == "FAILED" for p in report["payments"])
                            else "unconfirmed")
        return report

    def paid(self, provider_id, amount):
        return self.payment_report(provider_id, amount)["fullyPaid"]
