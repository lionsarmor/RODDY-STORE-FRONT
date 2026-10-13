# Printify merchandise for the RODDY storefront

Implemented: private account connection, product/variant discovery, storefront
color and size selection, matching mockups, variant prices, a variant-aware saved
cart, and US/Canada standard shipping estimates. The admin imports products,
refreshes stock and shipping, edits variant prices individually or in bulk, and
shows live production costs and gross margins privately.

Merchandise payment, address-specific shipping quotes, production submission and
tracking are **not yet implemented**. The product page lets customers save a
selection and clearly states that ordering opens soon. Existing Square software
checkout operates independently; the backend continues rejecting physical orders.

## Account setup

Create an API store and save the products in it. Generate a personal access token
under Printify → My Profile → Connections with `shops.read`, `products.read` and
`catalog.read`. Run this in the droplet console as root:

```sh
python3 /opt/roddy-store/backend/deploy/configure-printify.py
```

The hidden prompt verifies shops and product access, then saves
`/etc/roddy-store/printify.json` as root:roddystore with mode 640. Credentials are
read on demand; replacing the token needs no service restart. Do not paste tokens
into the catalog, GitHub, or chat. Replace a token that has been shared in chat.

## Product and variant sync

Open Admin → Printify merchandise and connect to GitHub as the store owner. Use
**Check connection & load products**, choose the matching storefront product, and
**Import options & shipping**. Existing mappings have a **Refresh stock, costs &
shipping** button. Review the draft, preview it, then publish.

- Only supplier-enabled combinations are imported. Color and size come from
  Printify option IDs, not text guessed from titles.
- Refresh preserves edited storefront prices and offer checkboxes for existing
  variants. It removes supplier-disabled variants and adds newly enabled variants
  at their saved Printify retail prices. Review new prices before publishing.
- Stock is a published snapshot. Refresh before updating the listing; it is not
  a live checkout stock check.
- Retail prices are USD. Production costs remain in the private admin response;
  they are not copied to the public catalog.
- Photos uploaded through the existing admin gallery are preserved. A selected
  variant can show its matching Printify mockup as the first gallery image.
- Use **Options & shipping** in a product editor for offline draft pricing and
  shipping country settings. Live costs require a refresh in the Printify panel.

### Launch pricing, 2026-10-13

| Product / size | Retail USD | Production cost USD | Gross profit USD |
| --- | ---: | ---: | ---: |
| Hoodie S–XL | 35.99 | 21.58 | 14.41 |
| Hoodie 2XL | 39.99 | 23.77 | 16.22 |
| Hoodie 3XL | 41.99 | 25.09 | 16.90 |
| Hoodie 4XL | 42.99 | 25.53 | 17.46 |
| Hoodie 5XL | 42.99 | 25.66 | 17.33 |
| Desk mat 12 × 18 | 17.99 | 10.67 | 7.32 |
| Desk mat 12 × 22 | 19.99 | 11.49 | 8.50 |
| Desk mat 16 × 32 | 27.99 | 15.60 | 12.39 |

Based on connected product costs at setup. Gross profit excludes payment fees,
taxes, returns and shipping. Customer shipping is separate. Storefront draft price edits do not change saved Printify listing prices.
The three desk-mat sizes were explicitly enabled through the owner-authorized
setup, with matching listing prices and separate print areas. The two smaller
sizes use 5610 × 3839 and 6791 × 3839 pixel artwork including template bleed;
the existing large mat placement was preserved. No supplier order was created.

### Shipping estimates

The integration reads the **v2 standard shipping** endpoint. The older v1 endpoint
can mix multiple shipping methods in its profiles, so it is not used. Matching
uses the provider's variant ID and destination country; only USD rates are accepted.

| Product | US first / additional | Canada first / additional |
| --- | --- | --- |
| Hoodie | $8.79 / $2.09 | $13.19 / $6.59 |
| Desk mat 12 × 18 | $7.39 / $6.00 | $14.09 / $6.09 |
| Desk mat 12 × 22 | $10.79 / $7.20 | $15.49 / $6.09 |
| Desk mat 16 × 32 | $10.79 / $7.20 | $15.49 / $6.09 |

The saved cart groups matching rates within each product. Different products are
estimated separately because they may ship separately. A missing rate is
unavailable, never implicitly free. These are provider standard-rate estimates,
not guaranteed final address-specific shipping charges or delivery times.

## Private API

- `GET /admin/printify?page=1`: store identity and paginated product/variant summaries.
- `GET /admin/printify/products/{product_id}`: selected product, actual options,
  variant prices/costs/availability, mockups, and standard shipping profiles.

Both endpoints require the configured GitHub administrator. They never return
the Printify token, raw provider error bodies or artwork print-area configuration.
Requests use fixed Printify hosts and bounded pagination; supplied pagination URLs
are never followed. A shipping permission/network failure keeps import available
with an explicit warning and no shipping rates.

## Remaining order integration

Before merchandise sales open, implement and validate:

- Server validation of mapped variants, current stock and retail prices.
- Customer address collection and Printify's address-specific shipping quote.
- Square verification and a durable fulfillment queue independent of the receipt page.
- Idempotent order references and reconciliation after ambiguous timeouts.
- Production release, shipment tracking and cancellation/refund handling.

This requires `orders.read` and `orders.write`, and appropriate webhook scopes.
Printify bills manufacturing and shipping separately from Square customer payments.
No supplier order or sample purchase was created during catalog setup.

References: [Printify API](https://developers.printify.com/),
[token setup](https://help.printify.com/hc/en-us/articles/4483626447249-How-can-I-generate-an-API-token).
