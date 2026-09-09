import { defineStore } from "pinia";
import { useCatalogStore } from './catalog';

export const useCheckoutStore = defineStore("checkout", {
  state: () => ({ loading: false }),

  actions: {
    /** items: [{ id, qty }] — same shape as the cart store's items. */
    async checkout(items) {
      if (!items.length) return;
      const catalog = useCatalogStore();
      if (catalog.preview) throw new Error('Checkout is disabled in draft previews.');
      if (!catalog.settings.checkoutEnabled || !/^https:\/\//.test(catalog.settings.checkoutEndpoint || '')) throw new Error('Online checkout is getting ready. Please check back soon.');
      if (this.loading) return;
      this.loading = true;
      try {
        const res = await fetch(catalog.settings.checkoutEndpoint.replace(/\/$/, '') + '/checkout', {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ items, requestId: crypto.randomUUID() }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.url) {
          throw new Error(data.error || "Checkout failed — please try again.");
        }
        if (!data.url.startsWith('https://checkout.stripe.com/')) throw new Error('Invalid checkout destination.');
        window.location.href = data.url; // leaving the page, no need to clear loading
      } catch (e) {
        this.loading = false;
        throw e;
      }
    },
  },
});
