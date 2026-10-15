// Deploy /backend to the droplet, then configure its HTTPS base URL in
// Admin → Checkout & Square (catalog.settings.checkoutEndpoint).

// Customer assets stay on the storefront. Admin publication becomes visible
// after the Pages deployment completes, together with its matching images.
export const CATALOG_URL = `${import.meta.env.BASE_URL}data/products.json`;

/** Resolve public assets on this site, without exposing repository links. */
export function rawAssetUrl(path) {
  return `${import.meta.env.BASE_URL}${path}`;
}
