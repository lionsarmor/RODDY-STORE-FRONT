import { defineStore } from "pinia";
import { CATALOG_URL, rawAssetUrl } from "../config";
import { normalizeCatalog, DEFAULT_SETTINGS } from '../catalog-model.js';
import { CATEGORY_PREVIEW_PARAM, categoryVisible, visibleProducts } from '../category-visibility.js';
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
    keycapProfiles: [],
    settings: { ...DEFAULT_SETTINGS },
    preview: false,
    categoryPreviewKey: new URLSearchParams(location.search).get(CATEGORY_PREVIEW_PARAM) || "",
    loaded: false,
    error: null,
  }),

  getters: {
    visibleCategories: state => state.categories.filter(c => categoryVisible(c, state.categoryPreviewKey, state.preview)),
    visibleProducts: state => visibleProducts(state.products, state.categories, state.categoryPreviewKey, state.preview),
    unlistedCategory: state => state.categories.find(c => c.visible === false && categoryVisible(c, state.categoryPreviewKey)) || null,
  },

  actions: {
    async load() {
      if (this.loaded) return;
      this.error = null;
      try {
        const url = CATALOG_URL;
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
        this.keycapProfiles = data.keycapProfiles;
        this.settings = data.settings;
        if (!this.preview && /^https:\/\//.test(this.settings.checkoutEndpoint || "")) {
          try {
            const response = await fetch(this.settings.checkoutEndpoint.replace(/\/$/, "") + "/inventory", {cache: "no-store"});
            if (response.ok) {
              const inventory = await response.json();
              for (const product of this.products) product.purchasingSuspended = [...(inventory.suspendedProducts || []),...(inventory.pricingPendingProducts || [])].includes(product.id);
              for (const price of inventory.prices || []) {
                const product=this.products.find(p=>p.id===price.id);if(!product)continue;
                product.dynamicPricing=true;
                const target=product.merch ? product.merch.variants.find(v=>v.id===price.variantId) : product;
                if(target && Number.isInteger(price.priceCents) && price.priceCents>0)target.price=price.priceCents/100;
                if(target && product.merch)target.available=price.available;
              }
              for (const item of inventory.items || []) {
                const product = this.products.find(p => p.id === item.id && p.type === "physical" && !p.merch);
                if (product && Number.isInteger(item.available) && item.available >= 0) product.stock = item.available;
              }
            }
          } catch { /* Backend checkout always revalidates stock. */ }
        }
        this.loaded = true;
      } catch (err) {
        this.error = err.message;
      }
    },

    byId(id) {
      return this.visibleProducts.find((p) => p.id === id) || null;
    },

    byCategory(categoryId) {
      if (!categoryId || categoryId === "all") return this.visibleProducts;
      return this.visibleProducts.filter((p) => p.category === categoryId);
    },

    categoryMeta(id) {
      return this.visibleCategories.find((c) => c.id === id) || null;
    },
  },
});

export function stockState(product) {
  if (product.purchasingSuspended) return 'out';
  if (product.status === 'coming-soon') return 'soon';
  if (product.supplier && !['office','manual','automatic'].includes(product.supplier.fulfillment)) return 'soon';
  if (product.status === 'sold-out') return 'out';
  if (product.merch && !product.merch.variants.some(v => v.enabled && v.available !== false)) return 'out';
  if (product.active && product.trackStock === false) return 'in';
  if (!product.active || product.stock <= 0) return "out";
  if (product.stock <= 5) return "low";
  return "in";
}

export function stockLabel(product) {
  if (product.purchasingSuspended) return 'Temporarily unavailable';
  const state = stockState(product);
  if (state === 'soon') return product.availabilityLabel || 'Coming soon';
  if (state === "out") return "Sold out";
  if (state === "low") return `Only ${product.stock} left`;
  return product.merch || product.keycaps ? "Made to order" : "In stock";
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
