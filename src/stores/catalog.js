import { defineStore } from "pinia";
import { CATALOG_URL, rawAssetUrl } from "../config";

/** Older catalog data (or a repo that hasn't been re-published since the
    single-photo -> multi-photo change) may still have a lone `image` string
    instead of `images: []`. Normalize on the way in so every consumer
    (storefront and admin) can assume `images` is always an array. */
export function normalizeProduct(product) {
  if (Array.isArray(product.images)) return product;
  const { image, ...rest } = product;
  return { ...rest, images: image ? [image] : [] };
}

export const useCatalogStore = defineStore("catalog", {
  state: () => ({
    categories: [],
    products: [],
    loaded: false,
    error: null,
  }),

  actions: {
    async load() {
      if (this.loaded) return;
      try {
        // In prod, read straight from GitHub instead of this site's own
        // (possibly stale, pre-rebuild) copy — see CATALOG_URL in config.js.
        const url = import.meta.env.DEV ? `${import.meta.env.BASE_URL}data/products.json` : CATALOG_URL;
        const res = await fetch(url, { cache: "no-store" });
        if (!res.ok) throw new Error(`Failed to load catalog: ${res.status}`);
        const data = await res.json();
        this.categories = data.categories;
        this.products = (data.products || []).map(normalizeProduct);
        this.loaded = true;
      } catch (err) {
        this.error = err.message;
      }
    },

    byId(id) {
      return this.products.find((p) => p.id === id) || null;
    },

    byCategory(categoryId) {
      if (!categoryId || categoryId === "all") return this.products.filter((p) => p.active);
      return this.products.filter((p) => p.active && p.category === categoryId);
    },

    categoryMeta(id) {
      return this.categories.find((c) => c.id === id) || null;
    },
  },
});

export function stockState(product) {
  if (!product.active || product.stock <= 0) return "out";
  if (product.stock <= 5) return "low";
  return "in";
}

export function stockLabel(product) {
  const state = stockState(product);
  if (state === "out") return "Sold out";
  if (state === "low") return `Only ${product.stock} left`;
  return "In stock";
}

export function formatPrice(amount) {
  return `$${Number(amount).toFixed(2)}`;
}

/** product.image is stored relative to the site root (e.g. "img/products/starfall.jpg"). */
export function productImageUrl(path) {
  return import.meta.env.DEV ? `${import.meta.env.BASE_URL}${path}` : rawAssetUrl(path);
}
