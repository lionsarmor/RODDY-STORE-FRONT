# RODDY STORE FRONT

RODDY ● Modern technology from a future we were promised.

A storefront for the RODDY brand — 14 palettes pulled straight from the
brand pack, a click-the-logo theme switcher, a product catalog, a real cart
that checks out once for everything through Stripe, and an admin page that
edits inventory by committing straight to this repo. Built with **Vue 3 +
Vite + Tailwind CSS v4 + Pinia**, deployed to GitHub Pages via GitHub
Actions, with one small Cloudflare Worker doing the one thing a static site
can't: creating the Stripe Checkout Session.

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
src/config.js                          the deployed checkout Worker's URL
src/styles/main.css                    Tailwind entry + design tokens (@theme block)
src/styles/themes.css                  per-theme CSS custom-property overrides
src/admin/                             admin mini-app: AdminApp.vue, api.js (GitHub Contents API), utils.js
src/order/                             order-confirmation mini-app
public/data/products.json              the product catalog — served as-is, this is what admin edits
public/img/logos/RODDY_SVG_BRAND_PACK/  source-of-truth logo assets, every palette
worker/                                Cloudflare Worker — the only server-side piece, creates
                                        one multi-item Stripe Checkout Session per cart
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

**Industrial is the default**, and its colors (`#ded1bf` capsule / `#000000`
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
- A small render-blocking inline script at the top of each HTML entry's
  `<head>` restores the saved theme from `localStorage` before Vue mounts,
  so there's no flash of the wrong palette.

Click the logo → cycles to the next theme. Click **Theme** → opens a swatch
grid (grouped like the list above) to jump straight to any of the 14.

## Editing products

Product data lives in `public/data/products.json`: a flat list with `sku`,
`name`, `category`, `price`, `stock`, `description`, and `specs`. There's no
image field — product art is generated from the brand badge mark itself (so
it always matches whatever theme is active) rather than requiring
photography. `price` and `name` are what the checkout Worker re-prices the
cart against, so they're the source of truth for what a customer is actually
charged.

Edit the file by hand and commit it, or use the admin page below.

## The admin page

`admin.html` (`src/admin/`) is a lightweight inventory editor. Since GitHub
Pages can't run a database or a server, it works by talking **directly to
the GitHub API from your browser** and committing the updated
`data/products.json` straight to this repo. The storefront and the checkout
Worker both read that file straight from `raw.githubusercontent.com`
(see `CATALOG_URL` in `src/config.js` and `PRODUCTS_URL` in
`worker/wrangler.toml`) rather than from the built `dist/` copy, so a
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
   checkout Worker reads this same file to price every cart.
4. Hit **Publish changes to GitHub** — commits the updated
   `data/products.json` straight to your branch. The storefront picks it up
   within moments (it reads the file directly from GitHub); the built site
   itself still rebuilds via Actions in the background, but you don't need
   to wait on that for inventory/price/stock changes to show up.

**About the token:** it's only ever used client-side to call
`api.github.com` directly — it never touches any third-party server. Check
"remember on this device" and it's kept in that browser's `localStorage`;
leave it unchecked and you'll paste it fresh each session. Anyone with the
token can write to this one repo, so treat it like a password, and revoke it
from GitHub any time.

## Checkout: how buying actually works

The cart works like a normal online store: add whatever you want, hit
**Checkout**, pay once for the whole order. The one thing a fully static
site genuinely can't do on its own is combine an arbitrary cart into a
single Stripe charge — that requires a Stripe secret key, which can never
live in browser JS. So there's exactly one small server-side piece:
**`worker/`**, a Cloudflare Worker that takes `{ items: [{ id, qty }] }` and
creates a real multi-item Stripe Checkout Session.

It re-prices every cart against the live `data/products.json` itself before
calling Stripe — the browser only ever sends product IDs and quantities,
never prices, so there's nothing for a tampered request to gain.

### Deploying the checkout Worker (one-time)

**1. Install dependencies**

```
cd worker
npm install
```

**2. Log in to Cloudflare**

```
npx wrangler login
```

Opens a browser window to authorize. The free tier is plenty for this.

**3. Point the config at your actual site**

Open `worker/wrangler.toml` and check these against your real GitHub Pages
URL and repo (pre-filled from this repo's git remote):

```toml
[vars]
SITE_URL = "https://lionsarmor.github.io/RODDY-STORE-FRONT"
PRODUCTS_URL = "https://raw.githubusercontent.com/lionsarmor/RODDY-STORE-FRONT/main/public/data/products.json"
ALLOWED_ORIGINS = "https://lionsarmor.github.io,http://localhost:5173,http://localhost:5175"
SHIP_TO_COUNTRIES = "US,CA"
```

- `SITE_URL` — the deployed site, used for Stripe's success/cancel redirect
  URLs.
- `PRODUCTS_URL` — reads straight from GitHub (not the deployed site) so the
  Worker re-prices against whatever the admin last published, not a
  possibly-stale pre-rebuild copy. Matches `CATALOG_URL` in
  `src/config.js` — keep both in sync if the username or repo name ever
  change.
- `ALLOWED_ORIGINS` — only these origins may call the Worker. Add any other
  local dev ports you use.
- `SHIP_TO_COUNTRIES` — countries Stripe will collect a shipping address
  for. Add more comma-separated ISO codes to ship internationally.

**4. Add your Stripe secret key**

```
npm run secret:stripe
```

Pastes it in as an **encrypted Worker secret** — never written to this
repo, never sent to the browser. Get the key from
[Stripe Dashboard → Developers → API keys](https://dashboard.stripe.com/apikeys)
(the **secret** key, not the publishable one — use a test-mode key first if
you want to try the flow before going live).

**5. Deploy**

```
npm run deploy
```

Prints your Worker's URL:

```
https://roddy-checkout.<your-subdomain>.workers.dev
```

**6. Wire the frontend to it**

Open `src/config.js` (repo root, not `worker/`) and paste that URL in:

```js
export const CHECKOUT_ENDPOINT = "https://roddy-checkout.<your-subdomain>.workers.dev";
```

Commit and push — the next GitHub Pages build picks it up.

### Where orders show up

Stripe collects the shipping address at checkout (so you have something to
mail to) and emails the buyer a receipt automatically. On your end, every
completed order shows up in
[Stripe Dashboard → Payments](https://dashboard.stripe.com/payments) —
that's your packing list. If you'd rather get pinged than check the
dashboard, turn on **Dashboard → Settings → Notifications → "email me about
new payments."**

**About stock counts:** because there's no database, stock numbers in
`products.json` are a soft ceiling the Worker checks at checkout time
(it'll reject a cart that asks for more than you have listed), not something
automatically decremented by sales. Update the count yourself after a sale
comes in.

### Changing something later

- **Update the Stripe key:** re-run `npm run secret:stripe` inside `worker/`.
- **Change allowed origins/countries:** edit `wrangler.toml`, then
  `npm run deploy` again.
- **Adjust checkout logic itself:** `worker/src/index.js`.

## Brand reference

The full brand map (mission, palettes, product families, the meaning of the
dot) is summarized on the in-app **About** page (`#/about`).

## Where this is headed

See [ROADMAP.md](ROADMAP.md) — the admin page is next up for a real
overhaul (search/filter, live preview, draft safety, drag-to-reorder).
