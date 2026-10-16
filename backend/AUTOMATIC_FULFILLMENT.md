# Automatic fulfillment and pricing holds

Mouser and Printify share durable product purchase suspensions. AliExpress and
Yuzu are named in the same administration controls and can use `FulfillmentHolds`
when their automatic adapters are connected. Their purchasing is not enabled by
this change. No invented supplier API or payment capability is advertised.

## Retail pricing and suspension

Under **Suppliers → Automatic retail pricing & live price status**, the owner
can enable one saved policy for Printify and automatic Mouser items. The initial
live policy uses 30% markup on landed cost, a 4% + $0.30 per-unit payment-fee
reserve, 10% allowance when supplier tax/fees cannot be quoted, and upward .99
rounding. All controls are adjustable. Product editors also support a minimum
automatic price or an explicit fixed-price override.

The calculation is `(landed cost × (1 + markup) + fixed fee) / (1 - fee rate)`.
Quoted shipping is subtracted from this total to produce the product price, then
shown separately at checkout: shipping is not added twice. These allowances are
estimates, not actual settled payment fees or guaranteed profit. The fulfillment
loss guard retains a minimum 4% + $0.30 reserve independently of these controls.

Listing estimates refresh roughly every 30 minutes, one product per worker tick.
Mouser estimates use the account's saved shipping address privately; Printify
uses US first-item shipping. Checkout obtains current costs and shipping for the
customer's actual destination and shows revised item prices before payment.
Changing pricing settings or product sourcing/floor invalidates cached estimates;
missing, stale, incomplete or unavailable estimates suspend the public offer
until refreshed. Supplier credentials, costs and destinations are never public.

Prices follow costs down as well as up. Paid orders keep their accepted totals;
a policy change invalidates unpaid quotes. Printify supplier tax is not known
until its order is created, so pricing uses the configured allowance and verifies
the reported cost before releasing production. Mouser previews include supplier
tax and fees. Fixed-price overrides still use the shared loss guard. Recorded
supplier order totals update sales expenses without overwriting manual invoices;
“remaining after recorded supplier costs” excludes unrecorded expenses and is
not presented as final profit.

A cost increase over the accepted Mouser quote stops fulfillment and suspends
new product purchases. Printify is checked before order creation and again with
supplier line costs, shipping and tax before releasing an on-hold order into
production. Unknown prices fail closed. Overruns flag the paid order for review.
Suspensions persist in SQLite, appear in Orders, block quote/checkout server-side,
and appear as “Temporarily unavailable” in the storefront's inventory overlay.
No confidential reason/cost goes to that public endpoint.

Publish reviewed retail prices, then clear the hold under **Orders → Purchasing
suspended · pricing review**. New checkout rechecks costs. Previously paid orders
retain their original price and require their own review. Refunds remain in
Square; placing a new supplier order manually before checking references risks
buying twice. Already issued external Square links cannot be invalidated by a
browser overlay; if one is paid after suspension, the worker holds fulfillment.

## Mouser account and product setup

Use the separate Order/Cart API key, billing details and exactly one identifiable
unexpired saved card in My Mouser. Full card data never goes through RODDY. Enable
**Automatic Mouser ordering** in Suppliers, then select **Automatic direct-to-
customer fulfillment** for a Mouser product. Existing manual order snapshots
stay manual. Disabling automatic ordering stops new quotes/submissions but still
allows status/history reconciliation for submitted orders.

US/Canadian checkout destinations remain as configured per product. We explicitly
send the customer's delivery address, request complete in-stock quantities,
request Mouser-paid customs/duties in the cart, use USD and taxable payment, and
choose the lowest returned prepaid UPS/FedEx/DHL/US Postal carrier rate. Bill-
recipient/freight-collect methods are excluded. Supplier address limits are
validated without truncating names or addresses. A destination lacking usable
rates, amounts, stock, address or payment data cannot check out automatically.
No special blind-packaging agreement is inferred from API access.

A live account/cart/order-summary check was run with `SubmitOrder: false` using
the configured account shipping address. The live response uses `OrderID: "0"`
for previews and `SecondaryShippingRate: -1` when `SecondaryCode: 0`; only that
unselected secondary service is treated as absent. Purchase tests use mocked
providers. No live purchase or card charge was made during implementation.

## Submission, reconciliation and visibility

Only the existing single-process fulfillment worker submits orders. It rechecks
Square payment, supplier totals, exact parts/quantities and the frozen customer
address. A durable `mouser_purchases` intent stores a unique 20-character PO and
claims the submitting state before the POST. The returned reference is saved
before any subsequent call. All order records remain in the default All orders
view. Supplier reference, status, shipment tracking and order-cost expense records
remain owner-visible; customer receipts omit internal supplier details. Printify
order snapshots can carry a different product ID; line matching then requires
the original order reference plus documented `metadata.external_id`, exact
variant and quantity, with no unmatched additional lines.

A timeout/crash after the submission claim never triggers another submission.
The worker looks up the exact PO in order history and validates reference, parts,
quantities and destination before linking the result. Unmatched/ambiguous outcomes
stay under review. Automatic orders cannot be reset using manual supplier actions.
Failures remain visible in Needs attention and Needs your action. Recorded supplier
order cost is not a claim of settled payment; verify final invoices in Mouser.

Mouser does not expose a maximum-price/idempotency parameter in this API. There is
an unavoidable interval between preview and submission: if the supplier changes
a total during it, the returned/history total is flagged and new purchases held.
Supplier-side charges already accepted or production already started cannot be
undone by a local hold. API outages/quotas stop new purchasing; they never fall
back to an assumed price or free shipping. Supplier history may lag submission.

Official references: [Mouser OpenAPI](https://api.mouser.com/api/docs/V1),
[Mouser guide](https://www.mouser.com/pdfDocs/api-guide.pdf),
[Printify order/cost fields](https://developers.printify.com/#orders).
