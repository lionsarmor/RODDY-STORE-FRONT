import { defineStore } from "pinia";
import { CHECKOUT_ENDPOINT } from "../config";

export const useCheckoutStore = defineStore("checkout", {
  state: () => ({ loading: false }),

  actions: {
    /** items: [{ id, qty }] — same shape as the cart store's items. */
    async checkout(items) {
      if (!items.length) return;
      this.loading = true;
      try {
        const res = await fetch(CHECKOUT_ENDPOINT, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ items }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.url) {
          throw new Error(data.error || "Checkout failed — please try again.");
        }
        window.location.href = data.url; // leaving the page, no need to clear loading
      } catch (e) {
        this.loading = false;
        throw e;
      }
    },
  },
});
