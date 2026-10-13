import { defineStore } from "pinia";
import { cartLineKey, hydrateLine } from "../merch.js";

const CART_KEY = "roddy:cart";

function readCart() {
  try {
    const raw = localStorage.getItem(CART_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (i) =>
        i &&
        typeof i.id === "string" &&
        Number.isInteger(i.qty) &&
        i.qty > 0 &&
        i.qty <= 99 &&
        (i.variantId === undefined || typeof i.variantId === "string"),
    );
  } catch (e) {
    return [];
  }
}

export const useCartStore = defineStore("cart", {
  state: () => ({
    items: readCart(), // [{ id, qty }]
  }),

  getters: {
    count: (state) => state.items.reduce((sum, i) => sum + i.qty, 0),
  },

  actions: {
    persist() {
      try {
        localStorage.setItem(CART_KEY, JSON.stringify(this.items));
      } catch (e) {
        /* storage unavailable */
      }
    },

    add(productId, qty = 1, maxQty = 99, variantId = "") {
      const existing = this.items.find((i) => cartLineKey(i.id, i.variantId) === cartLineKey(productId, variantId));
      qty = Math.min(99, Math.max(1, Math.trunc(Number(qty)) || 1));
      if (existing) existing.qty = Math.min(maxQty, existing.qty + qty);
      else this.items.push({ id: productId, qty, ...(variantId ? {variantId} : {}) });
      this.persist();
    },

    setQty(productId, qty, variantId = "") {
      if (qty <= 0) return this.remove(productId, variantId);
      const existing = this.items.find((i) => cartLineKey(i.id, i.variantId) === cartLineKey(productId, variantId));
      if (existing) existing.qty = qty;
      this.persist();
    },

    remove(productId, variantId = "") {
      this.items = this.items.filter((i) => cartLineKey(i.id, i.variantId) !== cartLineKey(productId, variantId));
      this.persist();
    },

    clear() {
      this.items = [];
      this.persist();
    },

    /** Joins cart entries against the loaded catalog for display. */
    hydrated(catalogStore) {
      return this.items
        .map((i) => {
          const product = catalogStore.byId(i.id);
          return product ? hydrateLine(i, product) : null;
        })
        .filter(Boolean);
    },
  },
});
