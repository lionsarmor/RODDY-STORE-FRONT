<script setup>
import { computed, ref, reactive, watch } from "vue";
import { useRoute } from "vue-router";
import {
  useCatalogStore,
  formatPrice,
  productImageUrl,
  stockState,
} from "../stores/catalog";
import { useCartStore } from "../stores/cart";
import { useCheckoutStore } from "../stores/checkout";
import { useUiStore } from "../stores/ui";
import { estimateShipping, variantLabel, cartLineKey } from "../merch.js";
import {profileFor,designError,designLabel} from '../keycaps.js';
const address = reactive({first_name: "", last_name: "", email: "", phone: "", country: "US", region: "", address1: "", address2: "", city: "", zip: ""});
const destination = computed(() => address.country);
const quote = ref(null);
const quoting = ref(false);
const quoteError = ref("");
const route = useRoute();
const catalog = useCatalogStore();
const cart = useCartStore();
const checkout = useCheckoutStore();
const ui = useUiStore();
const items = computed(() => cart.hydrated(catalog));
const missing = computed(() => cart.items.filter((i) => !catalog.byId(i.id)));
const total = computed(() =>
  items.value.reduce((sum, i) => sum + i.price * i.qty, 0),
);
const physical = computed(() =>
  items.value.some((i) => i.product.type !== "digital"),
);
const shipping = computed(() =>
  physical.value ? estimateShipping(items.value, destination.value) : 0,
);
function itemError(item) {
  if (item.product.keycaps) {
    const error = designError(item.design, profileFor(catalog, item.product));
    if (error) return error;
    if (["soon", "out"].includes(stockState(item.product)) || item.product.pricePending) return "Your design is saved. Ordering opens when this set is ready.";
    return "";
  }
  if (item.product.merch) {
    if (!item.variant || !item.variant.enabled) return "This selection is no longer offered. Choose a color and size on the product page.";
    if (item.variant.available !== true) return "This selection is unavailable. Choose another color or size.";
    return "";
  }
  if (item.product.price <= 0) return "Get free downloads from their product pages.";
  if (item.product.type === "digital" && item.qty !== 1) return "Choose one copy of this digital download.";
  if (item.product.type === "physical" && !item.product.trackStock) return "This office-shipped item needs inventory configured before checkout.";
  if (
    ["soon", "out"].includes(stockState(item.product)) ||
    item.product.pricePending
  )
    return "This item is not available to buy.";
  if (item.product.trackStock && item.qty > item.product.stock)
    return `Only ${item.product.stock} available. Reduce the quantity.`;
  return "";
}
const invalid = computed(
  () => missing.value.length > 0 || items.value.some(itemError),
);
watch(() => JSON.stringify([cart.items, address]), () => { quote.value = null; quoteError.value = ""; });
async function getQuote() {
  quoting.value = true; quoteError.value = ""; quote.value = null;
  const fingerprint = JSON.stringify([cart.items, address]);
  try {
    const res = await fetch(catalog.settings.checkoutEndpoint.replace(/\/$/, "") + "/quote", {
      method: "POST", headers: {"content-type": "application/json"}, body: JSON.stringify({items: cart.items, address})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not calculate shipping.");
    if (fingerprint === JSON.stringify([cart.items, address])) quote.value = data;
  } catch (e) { quoteError.value = e.message; }
  finally { quoting.value = false; }
}
async function checkoutAll() {
  if (invalid.value || (physical.value && !quote.value)) return;
  try {
    await checkout.checkout(cart.items, physical.value ? quote.value?.quoteId : "");
  } catch (e) {
    ui.toast(e.message);
  }
}
function updateQty(item, value) {
  cart.setQty(
    item.product.id,
    Math.min(
      item.product.type === "digital" ? 1 : 99,
      Math.max(1, Math.trunc(Number(value)) || 1),
    ),
    item.variantId || "",
    item.design,
  );
}
</script>
<template>
  <div class="mx-auto max-w-6xl px-6 py-12">
    <p class="eyebrow">RODDY / YOUR NEXT BIG IDEA</p>
    <h1 class="mb-8 mt-3 text-4xl font-extrabold tracking-tight">YOUR CART.</h1>
    <p v-if="route.query.canceled" class="notice mb-6">
      Checkout was canceled. Your cart is still here.
    </p>
    <div v-if="!catalog.loaded" class="empty-state">Loading your cart…</div>
    <div v-else-if="!cart.items.length" class="empty-state">
      Your cart is empty.
      <RouterLink to="/shop" class="text-button"
        >Explore the catalog ↗</RouterLink
      >
    </div>
    <div v-else class="grid gap-8 lg:grid-cols-[1.5fr_1fr]">
      <div>
        <div v-for="entry in missing" :key="cartLineKey(entry.id, entry.variantId, entry.design)" class="notice mb-4">
          An item is no longer in the catalog: {{ entry.id }}.
          <button class="text-button" @click="cart.remove(entry.id, entry.variantId, entry.design)">
            Remove
          </button>
        </div>
        <div
          v-for="item in items"
          :key="item.key"
          class="mb-4 flex flex-wrap items-center gap-5 border border-border bg-panel p-5"
        >
          <img
            v-if="item.product.coverImage || item.product.images[0]"
            :src="
              productImageUrl(item.variant?.image || item.product.coverImage || item.product.images[0])
            "
            :alt="item.product.name"
            class="h-20 w-20 object-cover"
          />
          <div class="min-w-0 flex-1">
            <RouterLink
              :to="`/product/${item.product.id}`"
              class="font-mono text-sm font-bold"
              >{{ item.product.name }}</RouterLink
            >
            <p v-if="item.design" class="mt-2 text-xs leading-relaxed">{{designLabel(item.design)}}</p>
            <p v-if="item.variant" class="mt-2 text-sm">{{ variantLabel(item.variant) }}</p>
            <p class="mt-2 font-mono text-xs text-text-dim">
              {{
                item.product.pricePending
                  ? "Pricing TBA"
                  : formatPrice(item.price) + " each"
              }}
              · {{ item.product.type }}
            </p>
            <p v-if="itemError(item)" class="mt-3 text-xs text-brand">
              {{ itemError(item) }}
            </p>
          </div>
          <label class="quantity-field"
            >Quantity<input
              :value="item.qty"
              type="number"
              min="1"
              :max="
                item.product.type === 'digital'
                  ? 1
                  : item.product.trackStock
                    ? Math.min(99, item.product.stock)
                    : 99
              "
              @change="updateQty(item, $event.target.value)"
          /></label>
          <button class="text-button" @click="cart.remove(item.product.id, item.variantId, item.design)">
            Remove
          </button>
        </div>
        <RouterLink to="/shop" class="text-button">← Keep exploring</RouterLink>
      </div>
      <section class="self-start border border-border bg-panel p-6">
        <h2 class="mb-6 font-mono text-base">ORDER SUMMARY</h2>
        <div class="mb-4 flex justify-between text-sm">
          <span>Subtotal</span><span>{{ formatPrice(total) }}</span>
        </div>
        <form v-if="physical" class="shipping-form mb-6" @submit.prevent="getQuote">
          <h3 class="font-mono mb-4">DELIVERY ADDRESS</h3>
          <div class="shipping-fields">
            <label>First name<input v-model="address.first_name" autocomplete="given-name" maxlength="80" required /></label>
            <label>Last name<input v-model="address.last_name" autocomplete="family-name" maxlength="80" required /></label>
            <label class="wide">Email<input v-model="address.email" type="email" autocomplete="email" maxlength="254" required /></label>
            <label class="wide">Phone<input v-model="address.phone" type="tel" autocomplete="tel" maxlength="30" required /></label>
            <label class="wide">Address<input v-model="address.address1" autocomplete="address-line1" maxlength="150" required /></label>
            <label class="wide">Apartment / suite (optional)<input v-model="address.address2" autocomplete="address-line2" maxlength="150" /></label>
            <label class="wide">City<input v-model="address.city" autocomplete="address-level2" maxlength="100" required /></label>
            <label>Country<select v-model="address.country" autocomplete="country"><option value="US">United States</option><option value="CA">Canada</option></select></label>
            <label>State / province code<input v-model="address.region" autocomplete="address-level1" placeholder="CA / ON" minlength="2" maxlength="2" required /></label>
            <label class="wide">ZIP / postal code<input v-model="address.zip" autocomplete="postal-code" maxlength="12" required /></label>
          </div>
          <button class="button w-full mt-4" type="submit" :disabled="quoting || invalid || catalog.preview">{{ quoting ? 'Calculating…' : 'Calculate shipping' }}</button>
          <p v-if="quoteError" class="release-note" role="alert">{{ quoteError }}</p>
          <p v-if="quote" class="text-xs mt-3">Shipping confirmed for this address. Quote valid for 15 minutes.</p>
        </form>
        <div class="mb-4 flex justify-between text-sm">
          <span>{{
            physical ? (quote ? "Standard shipping" : "Shipping estimate") : "Shipping"
          }}</span
          ><span>{{
            physical
              ? quote ? formatPrice(quote.shipping / 100) : shipping === null ? "Calculate above" : formatPrice(shipping)
              : "Not required"
          }}</span>
        </div>
        <div
          class="mb-5 flex justify-between border-t border-border pt-4 font-mono text-lg"
        >
          <span>Estimated total</span
          ><span>{{ formatPrice(quote ? quote.amountTotal / 100 : total + (shipping || 0)) }}{{ physical && !quote ? " (estimate)" : "" }}</span>
        </div>
        <p class="mb-5 text-xs leading-relaxed text-text-dim">
          {{ physical ? "USD. One payment covers your order. Downloads unlock after payment; made-to-order and office items ship separately." : "USD. Your software download appears after payment is confirmed." }}
        </p>
        <button
          class="button primary w-full"
          :disabled="
            checkout.loading ||
            invalid ||
            (physical && !quote) ||
            !catalog.settings.checkoutEnabled ||
            catalog.preview
          "
          @click="checkoutAll"
        >
          {{ checkout.loading ? "Opening checkout…" : "Secure checkout ↗" }}
        </button>
        <p v-if="!catalog.settings.checkoutEnabled" class="release-note">
          Checkout is getting ready. Your cart is saved on this device.
        </p>
        <p v-if="invalid" class="release-note">
          Update the unavailable items above to continue.
        </p>
        <p class="mt-4 text-center font-mono text-[9px] text-text-dim">
          SECURE PAYMENTS BY SQUARE
        </p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.shipping-fields { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
.shipping-fields label { display:grid; gap:6px; min-width:0; font-size:12px; }
.shipping-fields .wide { grid-column:1/-1; }
.shipping-fields input, .shipping-fields select { width:100%; min-width:0; background:var(--color-panel, #101115); color:inherit; border:1px solid var(--color-border, #444); padding:10px; font:inherit; }
</style>
