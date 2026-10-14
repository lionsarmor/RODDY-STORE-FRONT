# RODDY STORE FRONT

RODDY ● Play. Build. Make it yours.

A storefront for the RODDY brand — 14 palettes pulled straight from the
brand pack, a click-the-logo theme switcher, a product catalog, a real cart
with Square-hosted payment and private software downloads, and an admin page that
edits inventory by committing straight to this repo. Built with **Vue 3 +
Vite + Tailwind CSS v4 + Pinia**, deployed to GitHub Pages via GitHub
Actions, with a small Python backend on the existing DigitalOcean droplet for
checkout, payment verification, and paid ZIP delivery.

## Stack

- **Vue 3** (`<script setup>` SFCs) for components and routing (`vue-router`,
  hash mode)
- **Pinia** for state — theme, cart, catalog, UI (toast/overlay)
- **Tailwind CSS v4** for styling, wired to runtime CSS custom properties so
  theme switching needs no rebuild
- **Vite** for dev server + build, as a multi-page app (storefront, admin,
  order-confirmation are three separate bundles)

## Project layout

```
index.html, admin.html, order.html   Vite entry points (one per mini-app)
src/main.js                            storefront entry — mounts App.vue via vue-router
src/App.vue                            layout shell: header, footer, theme overlay, toast
src/router.js                          hash-based routes: / /shop /product/:id /cart /about
src/views/                             route components (Home, Shop, Product, Cart, About, NotFound)
src/components/                        RoddyLogo, AppHeader, AppFooter, ThemeOverlay, Toast, ProductCard
src/stores/                            Pinia stores: theme.js, catalog.js, cart.js, checkout.js, ui.js
src/theme-data.js                      the 14 palettes' metadata (id, logo asset, picker swatch)
src/config.js                          live catalog and asset URLs
src/styles/main.css                    Tailwind entry + design tokens (@theme block)
src/styles/themes.css                  per-theme CSS custom-property overrides
src/admin/                             admin mini-app: AdminApp.vue, api.js (GitHub Contents API), utils.js
src/order/                             order-confirmation mini-app
public/data/products.json              the product catalog — served as-is, this is what admin edits
public/img/logos/RODDY_SVG_BRAND_PACK/  source-of-truth logo assets, every palette
backend/                               FastAPI + SQLite service for Square checkout and
                                        private digital delivery, deployed on the droplet
.github/workflows/deploy.yml           builds with Vite and deploys dist/ to GitHub Pages
```

Anything in `public/` is served byte-for-byte at the site root — that's
deliberate for `data/products.json` (so the admin page's GitHub commits go
live without touching bundled JS) and for the large SVG library (no reason to
run 240+ hand-authored logo files through an asset pipeline).

## Running it locally

```
npm install
npm run dev
```

Vite serves the storefront at `http://localhost:5173/`, admin at
`/admin.html`, and the order-confirmation page at `/order.html`.

```
npm run build      # outputs to dist/
npm run preview    # serves the production build locally
```

Run `npm test` for the catalog and pricing checks. The supplier import browser
regression also checks selection before options load, retries, bulk review,
duplicate protection and the product editor. With a local dev server and
Playwright/Chromium available, run:

```sh
SUPPLIER_TEST_BASE_URL=http://localhost:5173 node tests/supplier-import.browser.mjs
```

If Playwright is installed elsewhere, set `PLAYWRIGHT_MODULE` to its absolute
`index.mjs` path. All external operations in this regression are mocked; it does
not publish catalog changes or place supplier orders.

## Deploying to GitHub Pages

This repo builds via GitHub Actions rather than serving raw files, since
Tailwind/Vue need a build step:

1. Push this repo to GitHub.
2. Repo → **Settings → Pages** → Source: **GitHub Actions** (not "Deploy
   from a branch").
3. Push to `main` — `.github/workflows/deploy.yml` runs `npm ci && npm run
   build` and deploys `dist/` automatically. First deploy takes a minute or
   two; check the **Actions** tab for progress.
4. Your store is live at `https://<your-username>.github.io/<repo-name>/`.

`vite.config.js` uses `base: "./"` (relative asset paths), so it works
correctly at any GitHub Pages subpath without needing the repo name hardcoded
anywhere.

## The theme system

`src/theme-data.js` lists 14 palettes, grouped the way the brand map
describes them — **Corporate** (Industrial, Blueprint), **Arcade** (five
neon colors), **Field** (Olive, Slate, Sand), **Pocket** (Mint, Lavender,
Peach), and **Collector** (Gold). Every hex value matches the actual SVGs in
`public/img/logos/RODDY_SVG_BRAND_PACK`, so when the theme changes, the
header/footer logo swaps to the real matching asset — never recolored in
CSS.

**First-time visitors get a random palette**, saved for later visits. A
visitor's theme-selector choice always takes priority. Industrial remains
the no-JavaScript fallback, and its colors (`#ded1bf` capsule / `#000000`
lettering / `#c32d28` dot) are pixel-matched to the literal master artwork in
`RODDY_SVG_BRAND_PACK/00_ORIGINAL_MASTERS`.

How it's wired:

- `src/styles/themes.css` holds the full CSS custom-property set per
  `[data-theme="…"]` value (industrial's values live directly in the
  `@theme` block in `main.css`, doubling as both the Tailwind token
  registration and the `:root` fallback).
- Tailwind reads those `--color-*` names to generate real utility classes —
  `bg-bg`, `text-text`, `bg-brand`, `border-border`, etc. — that stay live
  across theme changes because they resolve via `var()` at paint time, not
  at build time.
- `src/stores/theme.js` (Pinia) just toggles the `data-theme` attribute on
  `<html>` and persists the choice to `localStorage`.
- Vite inlines `src/theme-bootstrap.js` at the top of every HTML entry's
  `<head>`, using the IDs from the shared theme registry. Before first paint,
  it restores a valid saved theme or randomly selects and saves one of the
  14 palettes. Missing/obsolete choices and unavailable storage are handled;
  normal navigation and reloads preserve the saved choice.

Click the logo → cycles to the next theme. Click **Theme** → opens a swatch
grid (grouped like the list above) to jump straight to any of the 14.

## Editing products

Product data lives in `public/data/products.json`: a flat list with `sku`,
`name`, `category`, `price`, `stock`, `description`, `specs`, and `images`
(an array of paths under `public/img/products/`, in display order — the
first is the cover photo shown on the catalog card, and the product page
shows the full array as a carousel). `images` can be empty; product art then
falls back to the brand badge mark (so it always matches whatever theme is
active) instead of requiring photography. `price` and `name` are what the
checkout backend re-prices the cart against, so they're the source of truth
for what a customer is actually charged.

Edit the file by hand and commit it, or use the admin page below.

## The admin page

The admin is now the **RODDY Control Desk v2**. See [ADMIN-GUIDE.md](ADMIN-GUIDE.md)
for the current product, gallery, tag, homepage, free-download and Square workflows.
It includes local drafts, recovery, JSON backups, storefront previews, department
management and an authenticated order list.

`admin.html` (`src/admin/`) is the store control desk. Since GitHub
Pages can't run a database or a server, it works by talking **directly to
the GitHub API from your browser** and committing the updated
`data/products.json` straight to this repo. The storefront and the checkout
backend both read that file straight from `raw.githubusercontent.com`
(see `CATALOG_URL` in `src/config.js` and `PRODUCTS_URL` in
`backend/deploy/store.env.example`) rather than from the built `dist/` copy, so a
published change shows up on the live site within moments — it doesn't wait
on the GitHub Actions rebuild that redeploys the rest of the app.

### One-time setup

1. Go to **github.com → Settings → Developer settings → Personal access
   tokens → Fine-grained tokens → Generate new token.**
2. Scope it to **only this repository.**
3. Under **Repository permissions**, set **Contents: Read and write.**
   Nothing else is needed.
4. Set an expiration you're comfortable with.
5. Copy the token — GitHub only shows it once.

### Using it

1. Open `/admin.html` on your deployed site (it's not linked from the main
   nav on purpose — bookmark it).
2. Fill in your GitHub username, repo name, and branch (these auto-fill
   correctly on a standard `*.github.io` project page), paste the token, hit
   **Connect**.
3. Add, edit, or delete products. Stock counts and prices live here — the
   checkout backend reads this same file to price every cart.
4. Hit **Publish changes to GitHub** — commits the updated
   `data/products.json` straight to your branch. The storefront picks it up
   within moments (it reads the file directly from GitHub); the built site
   itself still rebuilds via Actions in the background, but you don't need
   to wait on that for inventory/price/stock changes to show up.

**About the token:** catalog reads and publication call `api.github.com`
directly. When you use Orders, the token is also sent over
HTTPS to your configured checkout backend, which verifies your identity with
GitHub against `ADMIN_GITHUB_LOGIN`. Only configure your own trusted backend
URL. The backend does not persist or log the token. Check
"remember on this device" and it's kept in that browser's `localStorage`;
leave it unchecked and you'll paste it fresh each session. Anyone with the
token can write to this one repo, so treat it like a password, and revoke it
from GitHub any time.

## Checkout and digital delivery

DESK COMMANDER is **$3.99 USD**. Weather Commander and Shadow Over Space remain
free downloads with direct release links and project GitHub buttons.

The storefront uses the droplet's separate `backend/` service and Square-hosted
checkout. The server reads trusted catalog prices, creates idempotent checkout
links, verifies completed USD payments, and serves private ZIPs through expiring
download links. No paid ZIP belongs in `public/`.

See [backend/README.md](backend/README.md) for deployment, Square account setup,
sandbox validation, private release installation, operational limits, and rollback.
Checkout stays disabled until credentials and payment/download tests are complete.
Physical orders, promotions, and automatic tax are not configured.

Run `npm test`, the Python backend tests documented above, and `npm run build`.
GitHub Actions runs these checks before deploying the frontend to Pages.
The backend is deployed separately to the droplet; a Pages deployment does not
update the running Python service.

## Brand reference

The full brand map (mission, palettes, product families, the meaning of the
dot) is summarized on the in-app **About** page (`#/about`).

## Where this is headed

See [ROADMAP.md](ROADMAP.md) — the admin page is next up for a real
overhaul (search/filter, live preview, draft safety, drag-to-reorder).
