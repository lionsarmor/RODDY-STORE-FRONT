# Roadmap

Where things stand: the storefront, theme system, and checkout (cart →
Stripe Checkout Session → Cloudflare Worker → order in the Stripe Dashboard)
all work end to end. The weak point now is the admin page — it does the
job, but editing more than a couple of products in it is tedious. That's
the headline priority below.

## Priority 1 — An admin page that's actually fun to use

The current admin (`src/admin/AdminApp.vue`) renders every product as a
fully-expanded form, all at once, with no search, no preview, and nothing
saved until you hit **Publish**. That's fine at 16 products; it won't be at
60. Concretely, today it's missing:

- **Draft safety.** `session.catalog` lives only in memory — refresh the tab
  or have it crash mid-edit and unpublished changes are just gone.
- **Any way to scan the catalog quickly.** Every product is a full open
  form; there's no collapsed summary view, no search, no filter by
  category/active/low-stock, no sort.
- **Any visual sense of the product.** No thumbnail, no indication of what
  the badge art will actually look like.
- **A preview of the result.** You're editing JSON fields blind — no view of
  the actual `ProductCard` or product page your changes will produce.
- **Duplicate.** Every similar product (a new color variant, a sequel) gets
  typed from scratch.
- **Reordering.** New products get unshifted to the top; there's no drag
  or manual sort.
- **Inline validation.** Nothing stops a duplicate SKU, an empty name, or a
  negative price before it's committed.
- **A safety check before publish.** "Publish changes to GitHub" commits
  immediately — no diff, no "here's what's about to go live."
- **Category management.** Categories are a hardcoded array in the JSON;
  admin can't add, rename, or reorder them.

### Phase 1 — safe and fast (do this first; low risk, no new architecture)

- Autosave the in-progress catalog to `localStorage`, independent from the
  connect-credentials draft that already exists; show an "unsaved changes"
  badge and warn on tab close.
- Collapse each product to a summary row (badge thumbnail, name, price,
  stock, live/hidden) that expands to the full editor on click.
- Search box + category/active/low-stock filters + sort, above the list.
- Inline validation: required name, unique `sku`/`id`, non-negative price —
  errors shown next to the field, not discovered after publishing.
- **Duplicate** button next to **Delete** on each product.
- Before publish, show a plain-language diff ("2 changed, 1 added, 1
  removed") and require a confirm — same one-commit publish flow underneath,
  just no more blind commits.

### Phase 2 — visual and fun (the "super fun and easy" part)

- Live preview pane: the actual `ProductCard` (and maybe the product page)
  rendered right next to the form, updating as you type — badge art, theme,
  price formatting, all real.
- Drag-to-reorder products, and drag between categories.
- A small category manager (add/rename/reorder) instead of hand-editing an
  array in the JSON.
- Color-coded low-stock/out-of-stock badges directly in the collapsed row,
  so problems are visible without opening anything.
- A little delight on successful publish (the brand dot flashing, a short
  animation) — small, optional, matches the "keep it fun" brand voice; not
  load-bearing.

### Phase 3 — real product photography (bigger; a deliberate decision, not assumed)

Right now every product's art is the generated badge mark — there's no
image field at all. If real photography is ever wanted:

- Add an optional `image` field to the product schema.
- Upload flow in admin that commits the file straight to
  `public/img/products/` via the same GitHub Contents API the token
  already has write access to (client-side resize/compress before upload).
- `ProductCard`/`Product.vue` prefer the photo when present, fall back to
  the badge mark when not — so nothing breaks for products that never get a
  photo.

This is a real scope increase (new schema field, new upload UI, new
fallback logic in two components), worth deciding on deliberately rather
than bundling into Phase 1/2.

### Phase 4 — fulfillment helpers (after the above, once there's real order volume)

- A small admin section that calls the Worker (new endpoint, reusing its
  Stripe secret) to list recent Checkout Sessions, so recent orders and
  inventory live in the same tab instead of switching to the Stripe
  Dashboard.
- Auto-flag products that are both **active** and **sold out**, as a
  restock-or-hide nudge.

## Explicitly not planned

Carried over from the architecture decisions already made — worth stating
so they don't get accidentally re-litigated later:

- **No traditional database/backend.** GitHub-commit admin + the one
  Cloudflare Worker stays the entire "server."
- **No automatic stock decrement on sale.** Stock stays owner-updated;
  Phase 4's fulfillment helper surfaces orders, it doesn't wire inventory to
  Stripe automatically.
- **No multi-user admin accounts.** Single-owner personal-access-token model
  stays unless that changes for a real reason.
