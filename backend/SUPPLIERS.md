# Mouser and AliExpress discovery and selected imports

## Existing architecture

The store uses Vue/Pinia, an existing product editor and a GitHub-hosted public
catalog (`public/data/products.json`). Square checkout, office inventory, Printify,
digital releases, forum and newsletters use the existing FastAPI/SQLite droplet
service. No new framework, database or alternate customer checkout is introduced.

This phase adds **Suppliers & imports** in admin: private connection management,
keyword search, exact listing lookup, preferred-store bookmarks, seller verification,
selected draft imports and fee-aware retail estimates. It does **not** enable direct
Mouser/AliExpress purchasing, automatic supplier charges or background supplier sync.
Connection and capability messages in admin make these boundaries explicit.

## Payment and billing

Customers pay RODDY through Square, which pays out to the owner's linked bank.
Supplier purchases are separate expenses against the owner's supplier account.
Square does not automatically split or forward checkout proceeds to suppliers.
The existing Printify flow verifies payment before creating/releasing production.

Mouser documents Order API use of a saved account card and account billing/shipping
settings. Search access is separate from Cart/Order access. AliExpress's current DS
order schema includes an optional `payment.try_to_pay` and says to authorize the
account as DS before enabling it. Neither a saved card nor product-search access
establishes that supplier purchasing/payment works for this store.

Do not collect/store card numbers or CVV here. Configure billing on supplier sites.
No tests or deployment scripts place real supplier orders or attempt real payments.

## Search connections

Sign into admin using the existing GitHub-owner connection, then open **Suppliers &
imports**. Save API credentials in its password fields over HTTPS:

- Mouser: Search API key from My Mouser → API access. No Order key is requested.
- AliExpress: approved Open Platform App Key and App Secret with Dropship search
  permission. Exact listing/SKU details also require an authorized buyer token.
  An affiliate-only application's permissions may be insufficient.

### AliExpress approved-account onboarding

Developer review approval is separate from application creation and buyer authorization.
In App Console choose **Drop Shipping → Create App**, name it **RODDY Store**,
and configure the exact callback shown in Suppliers admin:
`https://store-api.143-244-168-180.sslip.io/suppliers/aliexpress/callback`.
It is generated from the backend's trusted `STORE_PUBLIC_URL`, not a browser Host header.
Save App Key and App Secret in the private admin form. Then click **Authorize
AliExpress buyer**, open **Continue to AliExpress**, sign into the sourcing account
on AliExpress, approve access, and return to admin → Reload supplier settings.
Run a real keyword search and exact listing lookup to verify application permissions.
Passwords and API secrets must not be pasted into chat, public files, or URLs.

The owner-only start endpoint creates a ten-minute, single-use authorization ticket.
A top-level backend visit sets a Secure/HttpOnly/SameSite=Lax host cookie before
redirecting to AliExpress. Callback state is bound to that browser and the saved
application credentials; missing, expired, replayed or mismatched state is rejected.
Tickets and browser bindings are stored as hashes in SQLite. Changing credentials
or disconnecting invalidates pending flows and clears tokens from a different app.

The server exchanges the code using official GOP `/rest/auth/token/create` signing
(API path + sorted parameters, HMAC-SHA256), then saves access/refresh tokens and
expiry times privately. Before supplier reads it renews tokens within 30 minutes of
expiry using `/rest/auth/token/refresh`. **Renew buyer authorization** also allows
explicit renewal. If renewal expires or is revoked, authorize again. A manually
entered token has no automatic renewal metadata. Provider errors never echo tokens.
Testing/production application token lifetimes differ; use the returned durations,
not assumed thirty-day validity. Authorization does not enable supplier ordering.

### X16 keycaps manufacturer onboarding

Suppliers admin includes the existing **v05 AULA F87/F87 Pro ANSI 87-key, 80% TKL**
design, pinned to source revision `e0b66b85566b53df6d7770bc1ebc081df73d0756` in
`lionsarmor/x16-keycaps`. The original checkout was inspected read-only. Its inventory
has 87 keys, and the supplier package file hashes and ZIP integrity were checked.
An identical supplier ZIP is hosted under `public/merch/keycaps/`, with its SHA-256
recorded in `SHA256SUMS.txt`; it requires no GitHub access. No artwork was rebuilt.

`public/merch/keycaps/FULFILLMENT_REQUEST.txt` is an unsent inquiry for Goblintech.
The design already uses their ANSI80 template. Custom manufacturing and creator
programs are leads, not confirmation of per-customer drop shipping or a public API.
YUZU is linked as a no-minimum custom-set alternative; its external creator checkout
is not assumed to integrate with Square.

Request a quote, digital proof and one physical fit sample before enabling sales.
Confirm repeat one-set pricing, US/Canada shipping, neutral packaging, design SKU,
billing, order submission, tracking, defects and cancellations. Nothing sends this
inquiry, orders a sample, charges a card, or publishes a purchasable keycap listing.

Blank fields retain existing credentials. Values are cleared from the form after
saving and never echoed in responses, public catalog, GitHub, localStorage or logs.
The service writes an atomic mode-600 JSON file beside `STORE_DATABASE`, named
`suppliers.json` (override with `SUPPLIERS_CONFIG` if needed). Back up this file
privately with the order database. The service user must be able to write its parent
directory. Disconnect removes local credentials; revoke keys separately upstream.

An unconfigured API returns a clear connection error; external website search links
remain available. “Configured” means credentials are present, not verified. A pending-approval flag is displayed when applicable. A real
successful search/lookup is required to establish access. A successful live read records verification time and clears the pending flag.
No demo products are shown
as live supplier results. Automated tests use explicit mocked supplier responses.

Mouser uses official v1 keyword/part-number endpoints and schema. AliExpress uses
its official TOP transport at `https://api-sg.aliexpress.com/sync`, HMAC-SHA256
signing, millisecond timestamps and the current `keyWord`, `pageSize`, `pageIndex`
parameters from the Open Service documentation and downloadable Java SDK. No
arbitrary URL is fetched by the server. Item URLs are reduced to validated numeric
IDs and looked up through the fixed API host. Raw provider errors are never relayed.

Normalized searches/lookup results are privately cached for five minutes. Outbound
request budgets are durable and shared across callers: Mouser 25/minute and 900/day;
AliExpress 15/minute and 500/day. These conservative local budgets do not override
provider-specific quotas. Repeated identical requests use cache and cost no new API
call. Unknown currencies, prices and stock are not fabricated as USD/free/in stock.

## Preferred sellers and selected imports

Save a store's name, AliExpress Store ID and keywords in Preferred suppliers.
Entering an ID builds its official HTTPS store URL; pasting a `/store/NUMBER` URL
extracts the ID. The API also accepts an ID without a URL and rejects mismatched
ID/URL pairs. Use a store ID, not a product ID or seller member-account ID. The preferred store link
opens its complete public storefront. The keyword search API documented here does
not expose a guaranteed whole-seller catalog filter; do not claim a global MiSTer
search is all of Retro Castle's listings. Exact product lookup returns seller identity.
With an AliExpress favorite selected, importing requires a matching verified store ID.
For exhaustive seller enumeration, obtain a supported seller feed/permission first.

Only checked results import. “Select all” applies to eligible rows on the current
page. AliExpress requires choosing an exact supplier variant. Each selected variant
becomes its own draft in this phase; there is no invented Printify-compatible option
mapping. Duplicate provider + listing + variant identities are rejected. Imports
report independent successes/failures and never add the supplier's entire catalog.

Drafts have `active: false`, `status: coming-soon`, tracked stock zero, public
provenance under `supplier`, and `fulfillment: pending`. Internal supplier cost is
used for estimates but omitted from public product records. Use the normal editor
for categories, content, media, tags, price and visibility. Existing products are
preserved. Publish remains an explicit existing catalog action.

Estimates use integer cents, account for a configurable shipping/duty allowance,
estimated processing percentage/fixed fee, markup or target margin, minimum profit
and optional upward .99 rounding. They are per-unit estimates, not shipping quotes,
guaranteed profit or procurement totals. Unknown costs require manual pricing. MOQ,
order multiples, sub-cent component prices, taxes, promotion rules and live landed
cost still need validation before implementing supplier purchasing.

Pending supplier products cannot be purchased, even if an owner changes their
visibility/status to Available. Both frontend and checkout enforce this. An owner
may explicitly choose `fulfillment: office` only for goods they actually own, then
configure tracked office stock and shipping rates. Those sales use the existing
mixed-cart Square/office flow. Disconnecting provenance keeps content and does not
place/cancel supplier orders or alter live inventory.

## Remaining direct-fulfillment work

Before direct supplier sales become available, connect the appropriate ordering
permissions, verify account billing and destination support, implement real shipping
quotes and SKU/MOQ/stock/cost checks, persist supplier-order approval/outbox states,
reconcile uncertain submissions before retries, and support tracking, cancellations,
refund exceptions and separate shipments in mixed carts. Confirm supplier resale and
third-party shipping terms for this business. Automatic submission/payment should
follow successful approved-order validation, not be inferred from a saved card.

These tasks are intentionally not represented as completed by catalog search/import
capabilities. No enabled checkbox can bypass the checkout guard.

## Official references

- [Mouser Search API](https://www.mouser.com/en/api-search/): signup and 30/minute,
  1,000/day upstream limits; [OpenAPI schema](https://api.mouser.com/api/docs/V1).
- [Mouser Order API](https://www.mouser.com/en/api-order/): saved account cards,
  order options and real submission requirements.
- [AliExpress search documentation](https://openservice.aliexpress.com/doc/api.htm#/?path=aliexpress.ds.text.search&methodType=GET%2FPOST).
- [AliExpress exact listing documentation](https://openservice.aliexpress.com/doc/api.htm#/?path=aliexpress.ds.product.get&methodType=GET%2FPOST).
- [AliExpress DS order documentation](https://openservice.aliexpress.com/doc/api.htm#/?path=aliexpress.ds.order.create&methodType=GET%2FPOST).

The official Open Service documentation JSON and Java SDK were inspected during
implementation; third-party wrappers were not used to invent request schemas.

## Validation and deployment

```sh
.tools/checkout-venv/bin/python3.12 -m unittest discover -s backend -p 'test_*.py'
npm test
npm run build
git diff --check
```

Deploy `app.py`, `commerce.py`, `suppliers.py`, `supplier_clients.py` and
`aliexpress_auth.py` together.
Migration adds private preference/cache/budget tables at startup and does not modify
orders, forum, newsletter records, catalog or paid ZIPs. Preserve the existing 64KB
Caddy store cap. Only newsletter routes and supplier-preferences JSON accept that
larger application body limit; other requests retain their 8KB cap. Restart only
`roddy-store`. Keep an SQLite snapshot and backend rollback copy before deploying.
