<script setup>
import { computed, ref } from "vue";
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
const destination = ref("US");
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
  if (item.product.merch) {
    if (!item.variant || !item.variant.enabled) return "This selection is no longer offered. Choose a color and size on the product page.";
    if (item.variant.available !== true) return "This selection is unavailable. Choose another color or size.";
    return "Merchandise ordering opens soon. Your selection is saved.";
  }
  if (item.product.type !== "digital" || item.product.price <= 0)
    return "Checkout currently supports paid software downloads. Get free products from their product pages.";
  if (item.qty !== 1) return "Choose one copy of this digital download.";
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
async function checkoutAll() {
  if (invalid.value) return;
  try {
    await checkout.checkout(cart.items);
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
        <div v-for="entry in missing" :key="cartLineKey(entry.id, entry.variantId)" class="notice mb-4">
          An item is no longer in the catalog: {{ entry.id }}.
          <button class="text-button" @click="cart.remove(entry.id, entry.variantId)">
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
          <button class="text-button" @click="cart.remove(item.product.id, item.variantId)">
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
        <label v-if="physical" class="merch-destination mb-4">Shipping estimate for<select v-model="destination"><option value="US">United States</option><option value="CA">Canada</option></select></label>
        <div class="mb-4 flex justify-between text-sm">
          <span>{{
            physical ? "Standard shipping estimate" : "Shipping"
          }}</span
          ><span>{{
            physical
              ? shipping === null ? "To be confirmed" : formatPrice(shipping)
              : "Not required"
          }}</span>
        </div>
        <div
          class="mb-5 flex justify-between border-t border-border pt-4 font-mono text-lg"
        >
          <span>Estimated total</span
          ><span>{{ formatPrice(total + (shipping || 0)) }}{{ shipping === null ? " + shipping" : "" }}</span>
        </div>
        <p class="mb-5 text-xs leading-relaxed text-text-dim">
          {{ physical ? "USD. Shipping is an estimate; products may ship separately. Merchandise ordering opens soon." : "USD. Your software download appears after payment is confirmed." }}
        </p>
        <button
          class="button primary w-full"
          :disabled="
            checkout.loading ||
            invalid ||
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
          {{ physical ? "Your merchandise selections are saved. Remove merchandise to check out with software downloads." : "Update the unavailable items above to continue." }}
        </p>
        <p class="mt-4 text-center font-mono text-[9px] text-text-dim">
          SECURE PAYMENTS BY SQUARE
        </p>
      </section>
    </div>
  </div>
</template>
