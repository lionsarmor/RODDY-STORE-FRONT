# Automatic fulfillment and pricing holds

Mouser and Printify share durable product purchase suspensions. AliExpress and
Yuzu are named in the same administration controls and can use `FulfillmentHolds`
when their automatic adapters are connected. Their purchasing is not enabled by
this change. No invented supplier API or payment capability is advertised.

## Retail pricing and suspension

The owner controls product/variant retail prices and supplier import markup in
the existing editor. Quotes never overwrite those prices. Public catalog data
continues to omit supplier names, part numbers, credentials and procurement costs.

At checkout, a known Printify unit cost at/above retail suspends the product.
Mouser uses an exact combined cart, quantity, in-stock check and USD order preview.
Each item's supplier cost must be below its retail total. Landed cost must fit
retail plus customer shipping, less a conservative 4% + $0.30 payment-fee reserve.
The fee reserve is a pricing safeguard, not a claim about actual Square fees.
Mouser tax and additional fees are absorbed by retail markup; only its quoted
carrier charge is added to customer shipping. No automatic retail repricing.

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
remain owner-visible; customer receipts omit internal supplier details.

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
