// URL of the Cloudflare Worker that turns a cart into a real Stripe Checkout
// Session (see /worker). Deploy the worker (`npm run deploy` inside worker/),
// then paste its workers.dev (or custom) URL here.
export const CHECKOUT_ENDPOINT = "https://roddy-checkout.YOUR-SUBDOMAIN.workers.dev";

// Where the live product catalog actually lives. The admin page commits
// straight to public/data/products.json in this repo, but GitHub Pages only
// serves the *built* dist/ copy, which stays stale until the next Actions
// rebuild finishes. Reading raw.githubusercontent.com instead means a
// Publish shows up on the storefront within moments, not after a rebuild.
// Update these if this repo is ever forked or renamed.
const CATALOG_OWNER = "lionsarmor";
const CATALOG_REPO = "RODDY-STORE-FRONT";
const CATALOG_BRANCH = "main";
const CATALOG_RAW_BASE = `https://raw.githubusercontent.com/${CATALOG_OWNER}/${CATALOG_REPO}/${CATALOG_BRANCH}/public/`;

export const CATALOG_URL = `${CATALOG_RAW_BASE}data/products.json`;

/** Resolves a product image path (e.g. "img/products/starfall.jpg") the same
    way in dev and prod: same-origin while running locally so hand-edited or
    admin-staged files show up immediately, raw GitHub content in production
    so a published photo shows up without waiting on a rebuild. */
export function rawAssetUrl(path) {
  return `${CATALOG_RAW_BASE}${path}`;
}
