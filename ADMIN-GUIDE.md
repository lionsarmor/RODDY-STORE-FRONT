# RODDY Control Desk

Open `/admin.html` on the store, or the same path on your local Vite server.
The editor opens in local draft mode, so you can explore it without credentials.
Connect to GitHub before publishing. Nothing is deployed by merely opening or
previewing the editor.

## Products and departments

The curated catalog contains DESK COMMANDER in Apps, I KNOW WHAT I SAW in Games,
KEYCHAIN KREATURES in Pocket, and KESTREL COMPUTER in Computers. The latter two
are explicitly coming soon. The existing game price and stock are retained;
review them before enabling checkout. DESK COMMANDER has unannounced pricing.
DESK MAT and HOODIE are listed under Merch as coming-soon entries with
unannounced pricing. Add their images, specifications, prices and stock in
the product editor when ready. No AI-related claims were assigned to products
without confirmation.

Use Products to search/filter the catalog and open a single product editor.
You can create, duplicate, hide, feature, delete, and edit products. The
Departments panel controls navigation names, IDs and ordering.

- **Details:** name, stable URL ID, SKU, category, physical/digital type,
  short card description, full description, optional **Why we made it** maker's
  note, release note, tags and specifications. The first three specifications
  become product-page highlights; the complete spec sheet can be expanded below.
- **Images:** a single **At-a-glance / cover image** for cards, plus a separate
  ordered gallery for the full product page. Upload/drop images, add existing
  repo images or HTTPS image URLs, move images, and remove them from the draft.
  Images are converted to JPG up to 1600px; GIFs become stills.
- **Pricing:** USD selling price, original price for sale displays, stock,
  unlimited stock, availability, visibility and homepage featuring.
- **Links & downloads:** GitHub repository, public free-download URL, and an
  optional **Documentation / schematics URL** for manuals or repair resources.
  Documentation buttons only appear once a valid link is supplied; the hardware
  promise is not presented as an already-published download.
  Use a $0 price, turn off “Pricing to be announced”, and select Available to
  display the direct download button. Turn off stock tracking for unlimited
  downloads. Downloads bypass Stripe. Paid download URLs must not be stored here.

Tags have editable labels and colors. ESP32, AI Assisted, NO AI and FREE are
provided. Validation prevents contradictory AI tags and FREE on paid products.

Coming-soon, hidden, sold-out, and unannounced-price products cannot be bought.
The server enforces these restrictions too.

## Homepage

Edit the announcement, hero headline/introduction, CTA, featured heading,
manifesto, support email, and spotlight product. The spotlight uses the
product's cover, or an independently uploaded homepage override.
The shop's featured exhibit follows this same spotlight product selection and
uses its at-a-glance cover. Department pages and filtered results omit the
exhibit so shoppers can focus on the matching products.
Feature products from their Pricing tab to include them in the homepage lineup.
The 14-theme selector applies across the store and admin.

Brand marks use the original outlined SVG paths: the compact R-and-dot badge
for small marks and the full RODDY-and-dot lockup for headers and footers.
Use the shared `RoddyLogo` component instead of typing an R or substituting a font.
The yellow/gold theme uses a red dot so it remains visible on gold backgrounds.

## Drafts, previews and publishing

Changes autosave to browser storage, scoped by repository and branch. A
recovery banner lets you restore the draft after refreshing. Image-heavy
drafts may fill browser storage; use Export JSON as a backup when warned.
Exports contain catalog data, never connection credentials.

Preview opens the actual storefront with your draft, including staged images.
Preview checkout is disabled. Publish validates the catalog, uploads new
images, then commits the catalog using GitHub's file SHA to detect conflicts.
Images already uploaded during a failed publication may remain in the repo;
the catalog draft remains intact. Removing an image reference does not delete
the original repository file.

GitHub connection requires a fine-grained token with Contents: Read and write
for this repository. Connecting keeps an edited local draft and makes clear
that publishing it replaces the current remote catalog. If a recovered draft
was based on a different remote version, export it and merge with the latest
catalog rather than overwriting newer work.

## Stripe setup

This requires your Stripe and Cloudflare accounts. The account/payout details
are entered in Stripe, not stored in the publicly served catalog.

1. Open **Checkout & Stripe** in the admin.
2. In a terminal, enter the project's `worker` directory and run `npm install`.
3. Run `npx wrangler login`.
4. Check `worker/wrangler.toml`: site URL, catalog URL, allowed browser origins,
   and `ADMIN_GITHUB_LOGIN` should match your store. It is configured for
   `roddy.world` and owner `lionsarmor`.
5. Run `npx wrangler secret put STRIPE_SECRET_KEY`. Paste your **test** Stripe
   secret key at the prompt. The key goes into Cloudflare secret storage.
6. Run `npm run deploy` in `worker`, then copy the resulting HTTPS Worker
   **base URL** into the admin checkout server field.
7. Choose shipping countries/rate, promo-code support, and optional tax.
   Configure Stripe Tax registrations before enabling automatic tax.
8. Publish settings and use **Check connection**. This actually calls Stripe
   with the server credential, not just a superficial URL check.
9. Enable checkout and publish again. Complete a Stripe test order and check
   both the verified order return page and Admin → Orders.
10. Replace the Worker secret with your live key when ready for real sales.
    Test and live Stripe coupons/orders are separate.

Promotions are created directly in Stripe and do not wait for catalog Publish.
Codes accept letters/numbers, a percentage discount, optional maximum uses,
and an expiration. Customers enter codes on Stripe's checkout page. You can
enable/disable codes; the panel lists up to 100 recent Stripe codes, filtered
to those created for RODDY.

Orders loads real Stripe sessions with pagination. Only complete paid/no-payment-
required orders are confirmed by the storefront. Use Stripe's dashboard for full
customer/shipping details, receipts and refunds. Admin requests send your GitHub
token to your configured Worker to verify the owner; use only your own server URL.

## Operational boundaries

Stock and fulfillment are manual. The Worker checks current published stock
but does not reserve or decrement it, so simultaneous purchases can exceed stock.
Paid digital file delivery, automatic fulfillment, tracking emails, inventory
reservations and refunds inside the admin are not implemented. Add durable
inventory storage and verified Stripe webhooks before operating at volume.
Shipping currently uses one flat USD rate per physical order.

No live Stripe transaction or deployment is performed by the repository tests.
Run `npm test` for catalog/checkout/auth validation, and `npm run build` for
all three Vue entry points.

Implementation references: [Stripe Checkout sessions](https://docs.stripe.com/api/checkout/sessions/create),
[promotion codes on the pinned API version](https://docs.stripe.com/api/promotion_codes/create?api-version=2024-06-20),
and [Cloudflare secrets](https://developers.cloudflare.com/workers/configuration/secrets/).
