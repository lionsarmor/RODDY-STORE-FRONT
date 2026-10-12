# Printify setup for the RODDY hoodie and desk mat

Status: account connection and private product/variant discovery are implemented.
Customer size selection, physical checkout, shipping quotes, production submission,
and tracking delivery are **not yet implemented**. Physical products remain coming
soon. Existing Square digital checkout continues to operate independently.

## Connect the account

1. Create a [Printify account](https://printify.com/) and complete onboarding.
2. In Connections, generate an API token with `shops.read` and `products.read`.
   Those are sufficient for this setup stage. See the
   [official token instructions](https://help.printify.com/hc/en-us/articles/4483626447249-How-can-I-generate-an-API-token).
3. Create an API store named RODDY under My Stores → Add a new store → API.
   See [Printify's API setup instructions](https://developers.printify.com/#create-a-personal-access-token).
4. In the droplet console, run:

   ```sh
   python3 /opt/roddy-store/backend/deploy/configure-printify.py
   ```

   Paste the token only into the hidden prompt. The helper lists accessible stores,
   asks you to select one if necessary, verifies product access, and atomically
   saves `/etc/roddy-store/printify.json` as root:roddystore with mode 640. It does
   not alter Square credentials, restart services, or create any supplier orders.
5. Open the RODDY admin, connect to GitHub, and select **Printify merchandise →
   Check connection & load products**. Empty inventory is expected initially.

Create the hoodie and desk mat in that same Printify store. Use the original print
artwork and the provider's product templates; storefront mockup photos are not
automatically usable as production artwork. Enable the actual hoodie sizes/colors
and mat dimensions you intend to sell. Save both products, then reload the panel.

## Next integration stage

The product IDs, variant IDs and costs from the connected account are needed to
map the storefront's `hoodie` and `desk-mat` products. Choose retail prices and
shipping destinations after checking supplier costs. Keep the products unavailable
until the following flow is implemented and validated:

- Variant-aware cart and checkout with server-validated variant IDs and prices.
- Customer shipping address and a supplier shipping quote before payment.
- Square payment verification followed by a durable fulfillment queue, independent
  of whether the customer returns to the receipt page.
- An order reference and reconciliation for ambiguous provider timeouts to prevent
  duplicate manufacturing. Persist the supplier order ID before production release.
- Create and release Printify orders, then update production and shipment tracking.
- Refund/cancellation handling: a Square refund alone does not cancel manufacturing.

Order submission will need `orders.read` and `orders.write`, and other scopes as
required for shipping/catalog or webhook integrations. Do not enable Printify's
automatic production approval while testing the submission flow. Printify has its
own manufacturing/shipping billing, separate from Square customer payments. This
connection step has not placed a sample order or charged the account.

## Operations

`GET /admin/printify?page=1` requires the configured GitHub administrator. The
response contains store identity and product/variant summaries, never the Printify
token. Pagination is bounded and constructed using the fixed provider host; the
server does not follow pagination URLs supplied in API response data.

The connection file is read on demand, so replacing credentials with the helper
does not need a backend restart. Back up this file privately and rotate the token
through Printify before its expiration. A missing file reports "not connected";
API authentication and network errors are displayed without provider response bodies.
