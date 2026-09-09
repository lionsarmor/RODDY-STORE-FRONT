# RODDY roadmap

Control Desk v2 implements searchable product editing, separate cover/gallery
images, colored tags, free/GitHub links, product and department ordering,
draft recovery, backups, previews, homepage controls, Stripe checkout settings,
promotions and an authenticated order list. See [ADMIN-GUIDE.md](ADMIN-GUIDE.md).

The storefront has a new theme-aware landing page and a curated four-product
lineup, plus DESK MAT and HOODIE under Merch. Stripe is prepared for owner
setup; checkout is disabled by default.

## Next: production operations

- Complete Stripe test-mode setup, verify real test purchases, then configure
  live keys and accurate prices/stock before accepting real orders.
- Add a durable inventory store, reservations and signed Stripe webhooks for
  automatic stock updates and protection against simultaneous overselling.
- Add paid digital fulfillment and shipping/tracking workflows.
- Add order detail views, fulfillment status and operational reports.
- Add shipping zones/rates if a single flat rate is no longer sufficient.

## Future editing improvements

- Product variants and variant-specific inventory/prices.
- Rich description blocks and individual image captions.
- Storage beyond browser localStorage for large unpublished media libraries.
- Atomic catalog-and-image publishing and repository media cleanup.
- More than one store operator when there is a concrete need.
