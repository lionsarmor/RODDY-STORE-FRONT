<script setup>
import RoddyLogo from "./RoddyLogo.vue";
import { stockState, stockLabel, formatPrice, productImageUrl } from "../stores/catalog";

defineProps({ product: { type: Object, required: true } });
</script>

<template>
  <RouterLink
    :to="`/product/${product.id}`"
    class="flex flex-col border border-border bg-panel transition-transform hover:-translate-y-0.5"
  >
    <div class="bg-spec-grid relative flex aspect-[4/3] items-center justify-center border-b border-border">
      <span class="absolute left-2 top-2 border border-border bg-panel px-1.5 py-0.5 font-mono text-[0.6rem] tracking-wide text-text-dim">
        {{ product.sku }}
      </span>
      <span
        v-if="stockState(product) !== 'in'"
        class="absolute right-2 top-2 border px-1.5 py-0.5 font-mono text-[0.6rem] uppercase tracking-wide"
        :class="stockState(product) === 'out' ? 'border-border bg-panel text-text-dim' : 'border-brand bg-panel text-brand'"
      >
        {{ stockState(product) === "out" ? "Sold out" : "Low stock" }}
      </span>
      <img v-if="product.images?.[0]" :src="productImageUrl(product.images[0])" :alt="product.name" class="h-full w-full object-cover">
      <RoddyLogo v-else kind="badge" class="w-[72%]" />
    </div>
    <div class="flex flex-1 flex-col gap-1 p-4">
      <span class="font-mono text-[0.62rem] uppercase tracking-wide text-brand">{{ product.category }}</span>
      <h3 class="font-mono text-base">{{ product.name }}</h3>
      <p class="flex-1 text-sm text-text-dim">{{ product.description }}</p>
      <div class="mt-1 flex items-center justify-between gap-2">
        <span class="font-mono text-lg">{{ formatPrice(product.price) }}</span>
        <span class="font-mono text-[0.72rem] uppercase tracking-wide text-text-dim">{{ stockLabel(product) }}</span>
      </div>
    </div>
  </RouterLink>
</template>
