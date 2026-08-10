<script setup>
import { computed, ref } from "vue";
import { useCatalogStore, stockState, stockLabel, formatPrice } from "../stores/catalog";
import { useCartStore } from "../stores/cart";
import { useUiStore } from "../stores/ui";
import { useCheckoutStore } from "../stores/checkout";
import RoddyLogo from "../components/RoddyLogo.vue";
import SpectrumLoader from "../components/SpectrumLoader.vue";

const props = defineProps({ id: { type: String, required: true } });
const catalog = useCatalogStore();
const cart = useCartStore();
const ui = useUiStore();
const checkout = useCheckoutStore();

const product = computed(() => catalog.byId(props.id));
const state = computed(() => (product.value ? stockState(product.value) : "out"));
const qty = ref(1);

function addToCart() {
  cart.add(product.value.id, Math.max(1, qty.value || 1));
  ui.toast(`Added ${product.value.name} to cart`);
}
async function buyNow() {
  try {
    await checkout.checkout([{ id: product.value.id, qty: Math.max(1, qty.value || 1) }]);
  } catch (e) {
    ui.toast(e.message);
  }
}
</script>

<template>
  <div v-if="!catalog.loaded" class="mx-auto max-w-6xl px-6 py-16 font-mono text-text-dim">Loading…</div>

  <div v-else-if="!product" class="mx-auto max-w-6xl px-6 py-16">
    <div class="border border-dashed border-border p-12 text-center font-mono text-text-dim">
      Product not found. <RouterLink to="/shop" class="text-brand">Back to catalog →</RouterLink>
    </div>
  </div>

  <div v-else class="mx-auto grid max-w-6xl grid-cols-1 gap-10 px-6 py-12 sm:grid-cols-2">
    <div class="bg-spec-grid relative flex aspect-square items-center justify-center border border-border">
      <span class="absolute left-3 top-3 border border-border bg-panel px-1.5 py-0.5 font-mono text-[0.6rem] tracking-wide text-text-dim">
        {{ product.sku }}
      </span>
      <span
        v-if="state !== 'in'"
        class="absolute right-3 top-3 border px-1.5 py-0.5 font-mono text-[0.6rem] uppercase tracking-wide"
        :class="state === 'out' ? 'border-border bg-panel text-text-dim' : 'border-brand bg-panel text-brand'"
      >
        {{ state === "out" ? "Sold out" : "Low stock" }}
      </span>
      <RoddyLogo kind="badge" class="w-[40%]" />
    </div>

    <div>
      <span class="font-mono text-xs tracking-wide text-brand">{{ product.sku }} — {{ product.category.toUpperCase() }}</span>
      <h1 class="mb-3 mt-1 font-mono text-3xl leading-tight">{{ product.name }}</h1>
      <div class="mb-4 font-mono text-2xl">{{ formatPrice(product.price) }}</div>
      <p class="mb-6 max-w-[52ch] text-text-dim">{{ product.description }}</p>

      <p
        class="mb-6 font-mono text-sm uppercase tracking-wide"
        :class="state === 'low' ? 'text-brand' : state === 'out' ? 'text-text-dim' : 'text-text'"
      >
        <span class="text-brand">●</span> {{ stockLabel(product) }}
      </p>

      <div class="mb-6 flex flex-wrap items-center gap-3">
        <input
          v-model.number="qty"
          type="number"
          min="1"
          :disabled="state === 'out'"
          class="w-16 border border-border bg-panel px-2 py-3 text-center font-mono disabled:opacity-40"
        >
        <button
          type="button"
          :disabled="state === 'out'"
          class="border border-border px-5 py-3 font-mono text-xs uppercase tracking-wide transition-colors hover:bg-bg-alt disabled:opacity-40"
          @click="addToCart"
        >
          Add to cart
        </button>
        <button
          type="button"
          :disabled="state === 'out' || checkout.loading"
          class="border border-brand bg-brand px-5 py-3 font-mono text-xs uppercase tracking-wide text-white transition-opacity hover:opacity-90 disabled:opacity-40"
          @click="buyNow"
        >
          {{ checkout.loading ? "Redirecting to Stripe…" : "Buy now →" }}
        </button>
      </div>
      <SpectrumLoader v-if="checkout.loading" class="mb-6 -mt-3" />

      <div v-if="Object.keys(product.specs || {}).length" class="border-t border-border pt-4">
        <dl class="grid grid-cols-[max-content_1fr] gap-x-5 gap-y-2">
          <template v-for="(v, k) in product.specs" :key="k">
            <dt class="font-mono text-xs uppercase tracking-wide text-text-dim">{{ k }}</dt>
            <dd class="text-sm">{{ v }}</dd>
          </template>
        </dl>
      </div>
    </div>
  </div>
</template>
