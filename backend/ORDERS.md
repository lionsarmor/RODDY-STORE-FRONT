# Order desk and bookkeeping

All checkout attempts persist in the existing SQLite orders database, including
mixed carts. Only verified paid physical orders enter the fulfillment inbox.
Admin uses the existing GitHub-owner authorization; customer receipt tokens,
manufacturing recipes and supplier credentials never appear in CSV exports.

## Daily workflow

Orders opens **All orders** by default, including automatic Printify fulfillment,
digital purchases, unpaid attempts, refunds and manual shipments. It refreshes
every 30 seconds while visible; loaded history pages remain loaded. Use
**Show all / clear filters** to return to the complete history.

1. Open **Orders → Needs your action**. Copy delivery details or download the private
   packet. Keycap packets contain the frozen manufacturing JSON for each design;
   Mouser/AliExpress packets contain exact part/listing/variant IDs and quantities.
2. Place and pay for the supplier order yourself. Enter its order number and,
   optionally, the actual invoice total in USD. Click **Mark ordered**.
3. Open **Processing**. When dispatched, enter carrier and tracking, then click
   **Save tracking + mark shipped**. Tracking appears on the buyer's receipt page.
4. Use **Shipped** for completed dispatches and **Needs attention** for exceptions.
   Mixed orders can occupy more than one lane while separate parcels progress.
   **All orders** includes digital sales, unpaid attempts and refunds.

Mouser and AliExpress purchasing/payment are manual. Their stock and shipping
checks are read-only. Keycap purchasing is also manual; no browser purchasing bot
is installed. Printify production is automatic and appears in All orders and Processing,
with its supplier reference, status, last update and tracking.
Supplier-purchase automation requires a later explicit authorization and review.

Manual supplier products use `supplier.fulfillment: manual` and `trackStock: false`.
AliExpress requires the existing buyer connection and exact variant; checkout
checks current stock and tracked delivery availability. Mouser requires Search
API access, MOQ/order-multiple compliance and configured US/Canada shipping rates.
Pending Order/Cart API approval does not block manual Mouser purchasing.

## Records and exports

**Reports, CSV exports & tools** exports every matching record across all workflow
stages, regardless of the current lane. Dates, search and payment filters apply;
the visible page size never truncates an export. CSV timestamps are UTC.

- Order summary: sale reference, payment status, goods/shipping/tax, captured
  revenue, refunds and actual Square processing fees when available.
- Line items: purchased quantities, frozen prices/options and keycap revisions.
- Supplier expenses: actual entered invoice amounts, references, dates/currencies.
- Payment history: deduplicated observations from Square, retained after refunds.

**Refresh payment records** rechecks historical attempts against Square in batches.
The worker refreshes recent paid orders every five minutes and older paid orders
daily. Refunds stop future fulfillment/download authorization without deleting
captured revenue, purchase snapshots, invoices or historical packets. Blank fees
or tax indicate unverified values, rather than an assumed zero. Net after fees
excludes supplier expenses and is not a profit calculation. Invoice fields accept
only positive totals and reject a repeated supplier/reference on the same order.

Back up the actual `STORE_DATABASE` using SQLite's online backup API, together with
private packet directories and configuration. The live deployment currently uses
`/var/lib/roddy-store/orders-live.sqlite3`; sandbox data stays separate.

## Keycap profiles

Product pages refer to a profile through `keycaps.profileId`. Each profile selects
a display template, private manufacturing template, supported number-row modes,
symbols, arrow styles and defaults. X16 supports swatches/text; Standard ANSI 87
supports conventional legends. Install and validate a profile's private template
before publishing its purchasable product. Paid orders freeze the exact recipe;
later catalog changes never regenerate their manufacturing files.

The current keycap price is $99.99 with configured per-set shipping of $15 US or
$25 Canada. These are owner-authorized estimates, not supplier quotations. Both
profiles use the approved palette, and checkout validates every individual key
and printed-layer color. Customers can inspect the enlarged design but cannot
download the private manufacturing packet.

## Visibility regression check

Run `node tools/test-order-visibility.mjs` with Playwright installed in
`.tools/node_modules` (the same browser tooling used by the customer-guide builder).
It mounts the actual order component against read-only fixture APIs and checks
default history, automatic Printify fulfillment, digital orders, status refresh,
pagination, filter recovery, mobile layout and cleanup of the refresh timer.
It never submits a payment or supplier order.

## Automatic suppliers and pricing holds

Mouser automatic orders stay visible in All orders and Processing, with the supplier
reference, costs and tracking. Cost overruns also enter Needs your action and
Needs attention, and suspend new purchases of affected products. The purchase-hold
controls cover Printify, Mouser and future AliExpress/Yuzu adapters; those latter
two automatic integrations are not connected yet. See
[AUTOMATIC_FULFILLMENT.md](AUTOMATIC_FULFILLMENT.md) for activation and recovery.
