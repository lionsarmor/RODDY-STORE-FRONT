import { defineStore } from "pinia";
import { CATALOG_URL, rawAssetUrl } from "../config";
import { normalizeCatalog, DEFAULT_SETTINGS } from '../catalog-model.js';
export { normalizeProduct } from '../catalog-model.js';

/** Older catalog data (or a repo that hasn't been re-published since the
    single-photo -> multi-photo change) may still have a lone `image` string
    instead of `images: []`. Normalize on the way in so every consumer
    (storefront and admin) can assume `images` is always an array. */

export const useCatalogStore = defineStore("catalog", {
  state: () => ({
    categories: [],
    products: [],
    tags: [],
    settings: { ...DEFAULT_SETTINGS },
    preview: false,
    loaded: false,
    error: null,
  }),

  actions: {
    async load() {
      if (this.loaded) return;
      this.error = null;
      try {
        // In prod, read straight from GitHub instead of this site's own
        // (possibly stale, pre-rebuild) copy — see CATALOG_URL in config.js.
        const url = import.meta.env.DEV ? `${import.meta.env.BASE_URL}data/products.json` : CATALOG_URL;
        let source;
        if (new URLSearchParams(location.search).get('preview') === '1') {
          const draft = sessionStorage.getItem('roddy:preview');
          if (draft) { source = JSON.parse(draft); this.preview = true; }
        }
        if (!source) {
          const res = await fetch(url, { cache: "no-store" });
          if (!res.ok) throw new Error(`Failed to load catalog: ${res.status}`);
          source = await res.json();
        }
        const data = normalizeCatalog(source);
        this.categories = data.categories;
        this.products = data.products;
        this.tags = data.tags;
        this.settings = data.settings;
        this.loaded = true;
      } catch (err) {
        this.error = err.message;
      }
    },

    byId(id) {
      return this.products.find((p) => p.id === id && p.active) || null;
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
  if (product.status === 'coming-soon') return 'soon';
  if (product.status === 'sold-out') return 'out';
  if (product.active && product.trackStock === false) return 'in';
  if (!product.active || product.stock <= 0) return "out";
  if (product.stock <= 5) return "low";
  return "in";
}

export function stockLabel(product) {
  const state = stockState(product);
  if (state === 'soon') return 'Coming soon';
  if (state === "out") return "Sold out";
  if (state === "low") return `Only ${product.stock} left`;
  return "In stock";
}

export function formatPrice(amount) {
  return `$${Number(amount).toFixed(2)}`;
}

/** product.image is stored relative to the site root (e.g. "img/products/starfall.jpg"). */
export function productImageUrl(path) {
  if (!path) return '';
  if (/^https?:\/\//i.test(path) || /^data:image\/(jpeg|png|webp|gif);base64,/i.test(path)) return path;
  return import.meta.env.DEV ? `${import.meta.env.BASE_URL}${path}` : rawAssetUrl(path);
}
