# RODDY roadmap

Control Desk v2 implements searchable product editing, separate cover/gallery
images, colored tags, free/GitHub links, product and department ordering,
draft recovery, backups, previews, homepage controls, Square checkout settings
and an authenticated order list. See [ADMIN-GUIDE.md](ADMIN-GUIDE.md).

The storefront has a new theme-aware landing page and a curated four-product
lineup, plus DESK MAT and HOODIE under Merch. Square checkout and private digital delivery run in a separate droplet backend;
checkout is disabled until account setup and end-to-end testing are complete.

## Next: production operations

- Complete Square sandbox setup, verify payment and ZIP delivery, then configure
  live credentials and applicable tax treatment before accepting real orders.
- Add a durable inventory store, reservations and signed payment webhooks for
  automatic stock updates and protection against simultaneous overselling.
- Add paid-download email recovery and physical shipping/tracking workflows.
- Add order detail views, fulfillment status and operational reports.
- Add shipping zones/rates if a single flat rate is no longer sufficient.

## Future editing improvements

- Product variants and variant-specific inventory/prices.
- Rich description blocks and individual image captions.
- Storage beyond browser localStorage for large unpublished media libraries.
- Atomic catalog-and-image publishing and repository media cleanup.
- More than one store operator when there is a concrete need.
