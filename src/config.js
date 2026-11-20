export const STOREFRONT_ORIGIN = "https://roddy.world";
export const ADMIN_ORIGIN = "https://store-api.143-244-168-180.sslip.io";
export const PRIVATE_ADMIN = import.meta.env.MODE === "private-admin";
export const STOREFRONT_BASE = PRIVATE_ADMIN ? STOREFRONT_ORIGIN + "/" : import.meta.env.BASE_URL;
export const CATALOG_URL = `${STOREFRONT_BASE}data/products.json`;

/** Resolve public storefront assets independently of the private dashboard. */
export function rawAssetUrl(path) {
  return `${STOREFRONT_BASE}${path}`;
}
