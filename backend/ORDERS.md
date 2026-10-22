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

Explicitly archived canceled or unconfirmed test checkouts are omitted from the admin list,
search, and dashboard counts. Their records remain in the database and CSV
exports. Other unconfirmed checkouts, paid orders, refunds, and payments in
progress remain visible. An archived test reappears if payment processing, a
payment, or a refund is later recorded. Archiving alone does not cancel payment links.

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

AliExpress purchasing/payment remains manual. Mouser supports explicitly enabled
automatic fulfillment; existing manual orders remain manual. Keycap purchasing is also manual; no browser purchasing bot
is installed. Printify production is automatic and appears in All orders and Processing,
with its supplier reference, status, last update and tracking.
Supplier-purchase automation requires a later explicit authorization and review.

Manual supplier products use `supplier.fulfillment: manual` and `trackStock: false`.
AliExpress requires the existing buyer connection and exact variant; checkout
checks current stock and tracked delivery availability. Mouser requires Search
API access, MOQ/order-multiple compliance and configured US/Canada shipping rates.
Pending Order/Cart API approval does not block manual Mouser purchasing.

## Records and exports

Paid digital items have **Download ZIP** and **Create customer link** controls on
their order cards, including mixed orders. Each action rechecks payment against
Square and uses the exact purchased file snapshot. Owner downloads last 15
minutes; customer links last seven days and can be copied or opened in an email
draft. Every download rechecks refunds. Owner reissues work after the public
receipt's 30-day expiry without extending that receipt. No email is sent by
opening a draft, and public order lists/CSV exports contain no download tickets.

Free product and movie-edition downloads now collect an email and create a **$0
Free** order. The original edition is saved, duplicate request retries do not
create extra orders, and these records never enter Square checkout or supplier
fulfillment. The admin can filter free orders, search by email, issue another
download link, write a thank-you, and record the sent message. Revenue and paid
sale counts remain separate. A recorded download opening means the server
redirected to the public file; it does not prove the full transfer completed.
Existing direct asset URLs and historical downloads are not backfilled.

The free-download form's optional updates checkbox uses the existing newsletter
consent wording and saves an opt-in with source `free-download`. It starts
unchecked. Declining it still allows the download, and suppressed addresses are
never silently reactivated. Thank-you drafts are editable; occasional releases,
offers or giveaway links can be prepared through the existing newsletter tools
for the opted-in audience. Creating a free order does not send email.

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

Automatic pricing and supplier-cost expense reporting are described in
[AUTOMATIC_FULFILLMENT.md](AUTOMATIC_FULFILLMENT.md). Saved markup controls are in
Suppliers; all paid orders retain the amounts accepted at checkout.
