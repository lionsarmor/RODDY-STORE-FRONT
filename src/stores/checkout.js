import { defineStore } from "pinia";
import { useCatalogStore } from "./catalog";
import { checkoutDestination } from "../checkout-links";

export const useCheckoutStore = defineStore("checkout", {
  state: () => ({ loading: false, attempt: null }),

  actions: {
    /** items: [{ id, qty }] — same shape as the cart store's items. */
    async checkout(items) {
      if (!items.length) return;
      const catalog = useCatalogStore();
      if (catalog.preview)
        throw new Error("Checkout is disabled in draft previews.");
      if (
        !catalog.settings.checkoutEnabled ||
        !/^https:\/\//.test(catalog.settings.checkoutEndpoint || "")
      )
        throw new Error(
          "Online checkout is getting ready. Please check back soon.",
        );
      if (this.loading) return;
      this.loading = true;
      try {
        // Reuse the same reference after a network error so retries cannot create
        // multiple payment links for the same attempt. A changed cart starts anew.
        const cartKey = JSON.stringify(
          [...items].sort((a, b) => a.id.localeCompare(b.id)),
        );
        let attempt = this.attempt;
        try {
          attempt =
            JSON.parse(sessionStorage.getItem("roddy:checkout-attempt")) ||
            attempt;
        } catch {}
        if (
          !attempt ||
          attempt.cartKey !== cartKey ||
          Date.now() - attempt.created > 50 * 60 * 1000
        ) {
          attempt = {
            cartKey,
            requestId: crypto.randomUUID(),
            created: Date.now(),
          };
          try {
            sessionStorage.setItem(
              "roddy:checkout-attempt",
              JSON.stringify(attempt),
            );
          } catch {}
        }
        this.attempt = attempt;
        const res = await fetch(
          catalog.settings.checkoutEndpoint.replace(/\/$/, "") + "/checkout",
          {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ items, requestId: attempt.requestId }),
          },
        );
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.url) {
          throw new Error(data.error || "Checkout failed — please try again.");
        }
        const destination = checkoutDestination(data.url);
        if (!destination || !/^[A-Za-z0-9_-]{43}$/.test(data.sessionId || ""))
          throw new Error("Invalid checkout destination.");
        try {
          sessionStorage.setItem("roddy:last-order", data.sessionId);
        } catch {}
        // Browsers can restore this page from their back/forward cache after
        // canceled checkout, including its previous loading state.
        window.addEventListener(
          "pageshow",
          () => {
            this.loading = false;
          },
          { once: true },
        );
        window.location.href = destination;
      } catch (e) {
        this.loading = false;
        throw e;
      }
    },
  },
});
