# Mixed checkout and fulfillment

RODDY uses one Square-hosted payment for digital downloads, Printify merchandise
and items shipped from the owner's office or manually ordered from suppliers.
Card details stay with Square. See [ORDERS.md](ORDERS.md) for the order desk.

## Configuration

The existing private `store.env` needs `STORE_CHECKOUT_ENABLED=true`,
`STORE_PHYSICAL_ENABLED=true`, and `STORE_FULFILLMENT_WORKER=true`. Run the service
with one uvicorn process, as in the supplied systemd unit. The worker polls pending
payments every 30 seconds and paid orders every five minutes, independently of
whether customers return to their receipt page. Keep the droplet and its SQLite
DB backed up; use SQLite's backup API rather than copying a live WAL database.

Printify requires `shops.read`, `products.read`, `catalog.read`, `orders.read`
and `orders.write`. Tokens stay in `/etc/roddy-store/printify.json`; Square
credentials stay in `/etc/roddy-store/store.env`. A funded Printify account/payment
method is required: Printify charges the owner separately for manufacturing,
shipping and any supplier taxes. Customer payment does not fund Printify directly.

## Customer flow

1. Add any available paid products to the cart. Free products download directly.
2. Physical carts collect a US/Canadian address, email and phone.
3. Calculate shipping: Printify quotes the actual product/variant/quantity/address
   combination; office rates come from the published product configuration.
4. The server stores a 15-minute quote. Changing the cart/address invalidates it.
   Checkout revalidates supplier stock, prices and available office inventory.
5. One itemized Square payment includes goods and shipping. The fixed delivery
   address is the address entered on RODDY; Square does not ask for a second one.
6. Only the correct completed USD payment unlocks downloads and creates
   fulfillment work. Office inventory is deducted exactly once.
7. The private order page shows downloads and separate shipment tracking.
   Square sends its payment receipt. Printify shipping notifications are enabled.

Automatic sales-tax calculation, discounts and label purchasing are not provided.
Totals currently include product prices and shipping; merchant tax setup remains
an operational responsibility. Digital quantity is limited to one per product.

## Office products: Link Commander and Keychain Kreatures

In **Products → Options & shipping**, enable US and/or Canada and enter first-item
and additional-item rates in USD. A missing country/rate blocks purchase rather
than becoming free shipping. Rates are per product; different office products'
charges add together. Publish these settings with the catalog.

In **Orders → Stock you ship from RODDY**, set live on-hand stock. The catalog stock seeds
new products only. Publishing an old catalog never restores sold stock. Unpaid
checkouts reserve stock; paid orders deduct it once. Abandoned hosted links are
canceled after one hour before their reservations are released. The owner can
also cancel an unpaid checkout in Orders. Stock cannot be set below reservations.
Set the product price and availability to Available only when ready to ship.
Link Commander starts hidden/coming soon with no price or shipping rates. Keychain
Kreatures keeps its existing coming-soon status; shipping is left unset.

Open **Orders → To order / send**, pack office items to the displayed
address, then enter carrier/tracking and mark shipped. Tracking appears on the
customer's private order page. Refunds do not automatically put stock back: inspect
returned goods and explicitly restock if appropriate.

## Printify recovery

Each supplier order uses `RODDY-<checkout request UUID>` and contains only Printify
lines, with the exact provider variant IDs and quantities. Digital/office lines
never go to the supplier. A queued job is durably marked submitting before POST.
A timeout or process crash with an unknown outcome never blindly repeats that
POST. The worker searches supplier orders for its reference. **Needs attention**
shows exceptions; **Find existing Printify order** links a matching external order.
If none is found, inspect Printify, resolve the issue there and use that same
external reference when creating an order manually, then reconcile it here.

Production is triggered explicitly once Printify reports an on-hold order with no
production timestamp; already-started production is not resubmitted. Payment,
stock/address, cost, or supplier issues remain visible in admin. Polling refreshes
production and tracking. A refund blocks new downloads and further automatic
production but cannot recall a parcel or undo manufacturing already started.
Review both Square and Printify before refunding/canceling a paid physical order.

## API and validation

Public: `POST /quote`, `POST /checkout`, `POST /order`, `GET /inventory`,
`GET /download/{ticket}`. Admin endpoints require the configured GitHub owner:
`GET /admin/orders`, `GET /admin/inventory`, `POST /admin/inventory/{product}`,
`POST /admin/orders/{reference}/shipment`, `/cancel`, `/reconcile`.
No customer addresses, private file hashes or bearer receipt sessions enter the
public catalog. Order references remain URL fragments; API responses are no-store.

Run `npm test`, `npm run test:backend`, `npm run build`. The mixed checkout tests
mock payment/production (including ambiguous POST recovery, refunds and inventory
contention). Live checks create shipping quotes and unpaid payment links only;
no real payment, manufacturing order or sample is purchased by validation.

References: [Printify orders and shipping](https://developers.printify.com/#orders),
[Square checkout](https://developer.squareup.com/docs/checkout-api).
