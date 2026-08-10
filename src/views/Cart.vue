<script setup>
import { computed } from "vue";
import { useCatalogStore, formatPrice, productImageUrl } from "../stores/catalog";
import { useCartStore } from "../stores/cart";
import { useCheckoutStore } from "../stores/checkout";
import { useUiStore } from "../stores/ui";
import RoddyLogo from "../components/RoddyLogo.vue";
import SpectrumLoader from "../components/SpectrumLoader.vue";

const catalog = useCatalogStore();
const cart = useCartStore();
const checkout = useCheckoutStore();
const ui = useUiStore();

const items = computed(() => cart.hydrated(catalog));
const total = computed(() => items.value.reduce((sum, i) => sum + i.product.price * i.qty, 0));

async function checkoutAll() {
  try {
    await checkout.checkout(cart.items);
  } catch (e) {
    ui.toast(e.message);
  }
}
</script>

<template>
  <div class="border-b border-border py-10">
    <div class="mx-auto max-w-6xl px-6">
      <h1 class="mb-2 font-mono text-3xl uppercase tracking-wide">Your cart</h1>
      <p class="max-w-[60ch] text-text-dim">
        Add whatever you want, then pay once for the whole order through Stripe's secure checkout.
      </p>
    </div>
  </div>

  <div class="mx-auto max-w-6xl px-6 py-12">
    <div v-if="!items.length" class="border border-dashed border-border p-12 text-center font-mono text-text-dim">
      Your cart is empty. <RouterLink to="/shop" class="text-brand">Browse the catalog →</RouterLink>
    </div>

    <template v-else>
      <div class="flex flex-col gap-4">
        <div
          v-for="item in items"
          :key="item.product.id"
          class="grid grid-cols-1 gap-4 border border-border bg-panel p-5 sm:grid-cols-[max-content_1fr_max-content] sm:items-center"
        >
          <div class="bg-spec-grid relative flex h-16 w-16 min-h-0 flex-shrink-0 items-center justify-center border border-border">
            <img v-if="item.product.images?.[0]" :src="productImageUrl(item.product.images[0])" :alt="item.product.name" class="h-full w-full object-cover">
            <RoddyLogo v-else kind="badge" class="w-[62%]" />
          </div>
          <div>
            <p class="font-mono text-base">{{ item.product.name }}</p>
            <p class="font-mono text-xs text-text-dim">
              {{ item.product.sku }} · Qty {{ item.qty }} · {{ formatPrice(item.product.price) }} each
            </p>
          </div>
          <button
            type="button"
            class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim hover:text-brand"
            @click="cart.remove(item.product.id)"
          >
            Remove
          </button>
        </div>
      </div>

      <div class="mt-6 flex flex-col gap-3 border border-border p-5">
        <div class="flex justify-between font-mono text-sm">
          <span>Items</span><span>{{ items.reduce((s, i) => s + i.qty, 0) }}</span>
        </div>
        <div class="flex justify-between border-t border-dashed border-border pt-2 font-mono text-lg">
          <span>Total</span><span>{{ formatPrice(total) }}</span>
        </div>
        <SpectrumLoader v-if="checkout.loading" />
        <button
          type="button"
          :disabled="checkout.loading"
          class="border border-brand bg-brand px-5 py-3 font-mono text-xs uppercase tracking-wide text-white transition-opacity hover:opacity-90 disabled:opacity-40"
          @click="checkoutAll"
        >
          {{ checkout.loading ? "Redirecting to Stripe…" : "Checkout →" }}
        </button>
      </div>
    </template>
  </div>
</template>
