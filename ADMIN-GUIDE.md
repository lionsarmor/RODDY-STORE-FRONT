# RODDY Control Desk

Open `/admin.html` on the store, or the same path on your local Vite server.
The editor opens in local draft mode, so you can explore it without credentials.
Connect to GitHub before publishing. Nothing is deployed by merely opening or
previewing the editor.

## Products and departments

The curated catalog contains DESK COMMANDER in Apps, I KNOW WHAT I SAW in Games,
KEYCHAIN KREATURES in Pocket, and KESTREL COMPUTER in Computers. The latter two
are explicitly coming soon. The existing game price and stock are retained;
review them before enabling checkout. DESK COMMANDER is a paid $3.99 USD software download.
DESK MAT and HOODIE have Printify color/size options, retail prices and standard
shipping estimates under Merch. Customers can browse and save selections;
merchandise ordering opens after physical checkout and production are integrated. No AI-related claims were assigned to products
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
  downloads. Downloads bypass paid checkout. Paid download URLs must not be stored here.

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
Preview checkout is disabled. Publish fetches the latest GitHub catalog and
reapplies only the fields changed since your draft began. Edits to different
fields combine automatically, including product edits alongside checkout settings.
If the same field changed in both versions, choose **Keep my edit** or
**Keep GitHub version**, apply the choices, review, then publish again.
Publish validates the merged catalog, uploads new images, then commits using
GitHub's file SHA. A further concurrent change stops publication safely; retry
Publish to fetch and merge again.
Images already uploaded during a failed publication may remain in the repo;
the catalog draft remains intact. Removing an image reference does not delete
the original repository file.

GitHub connection requires a fine-grained token with Contents: Read and write
for this repository. **Update from GitHub · keep edits** and connecting also
merge the latest catalog without discarding current edits. Drafts store their
original catalog for recovery. To recover a draft from an older editor version,
connect first, then click **Restore draft**; its original revision is retrieved
from GitHub. Drafts with neither an original catalog nor a revision cannot be
automatically merged safely. Keep an exported backup for those drafts.

## Printify merchandise setup

Open **Printify merchandise** to connect a Printify API store and inspect its
hoodie sizes/colors and desk-mat variants. The token is entered only in the
droplet console; the panel uses your GitHub administrator login to read the
private connection. The panel also offers the white/red RODDY hoodie print PNG.
Follow [backend/PRINTIFY.md](backend/PRINTIFY.md). This is account/product setup;
customer merchandise checkout and automatic fulfillment are not implemented yet.

## Square checkout and delivery

Use **Checkout & Square** to configure the HTTPS backend URL and check the
connection. The payment account, payout bank, access token, and location ID are
configured privately on Square and the droplet, never in the public catalog.

Follow [backend/README.md](backend/README.md) for server deployment and sandbox
setup. Keep public checkout disabled until a Square sandbox payment and private
ZIP download have both been verified. The connection check reports account
readiness, sandbox/live mode, and the server's separate checkout switch.

The backend currently accepts paid digital downloads only, one copy per product.
Install approved ZIPs in its private files directory and map product IDs to
filenames and SHA-256 hashes in its protected manifest. Do not publish paid file
URLs in the product editor. Removing an old public link cannot remove earlier
GitHub releases, history, or customer copies.

After verified payment, the order page provides 15-minute download links that can
be refreshed for 30 days. The page's fragment contains a private receipt token;
customers should bookmark it privately. Automatic email delivery and recovery are
not implemented; use the Square receipt for support. Refunds block new downloads.

Orders displays the most recent 100 checkout attempts and their last verified
status. Use Square's dashboard for current transactions, customer receipts,
refunds, and disputes. The GitHub token is sent to your configured backend to
verify the store owner; only configure your own trusted HTTPS endpoint.

Physical fulfillment, promotions, automatic tax, and automated dispute handling
are not configured. Arrange applicable tax treatment before enabling live sales.

Validation: `npm test`, `python3 -m unittest discover -s backend -p 'test_*.py'`,
and `npm run build` after installing the backend dependencies in a virtual
environment. Repository tests use a fake provider and do not make real charges.

## Printify merchandise options

Open **Printify merchandise** to load products from the connected account. Choose
which storefront product each Printify product belongs to, then import its options
and shipping. Existing products have **Refresh stock, costs & shipping**. A refresh
preserves edited retail prices and offer checkboxes, removes variants disabled in
Printify, and imports newly enabled variants at their saved Printify retail price.
Review changes and click **Publish** to update the live catalog.

Each mapped product shows its exact color/size combinations. Filter by size or
color, enter a bulk price, and apply it to the filtered rows. You can edit each
price or uncheck combinations you do not want to offer. Gross profit and margin
use live production costs and exclude payment fees, taxes, shipping and returns.
Those private production costs are never published into the storefront catalog.

The product editor also has **Options & shipping** for draft price edits and
US/Canada shipping settings. Standard shipping is imported from Printify and
shown per first/additional item. Missing rates are shown as unavailable. It is an
estimate until an address-specific checkout quote is implemented.

Current hoodie listing: 10 colors, sizes S–5XL, 76 combinations (4XL/5XL have 8
colors). Current desk mat listing: 12 × 18, 12 × 22 and 16 × 32 inches, each with its own print artwork and price. Enable and save new variants in
Printify, then refresh and review their artwork, retail prices and shipping.

See [backend/PRINTIFY.md](backend/PRINTIFY.md) for account setup and remaining
payment, production and tracking integration. No production order is created by
importing, refreshing or publishing the catalog.
