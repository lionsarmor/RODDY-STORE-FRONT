<script setup>
import { computed } from "vue";
import { useCatalogStore } from "../stores/catalog";
import ProductCard from "../components/ProductCard.vue";

const catalog = useCatalogStore();
const featured = computed(() => catalog.products.filter((p) => p.featured && p.active));
</script>

<template>
  <section class="border-b border-border py-16 sm:py-20">
    <div class="mx-auto max-w-6xl px-6">
      <p class="mb-4 font-mono text-xs uppercase tracking-widest text-brand">
        RODDY <span class="text-[0.7em]">●</span> Modern technology from a future we were promised.
      </p>
      <h1 class="mb-4 font-mono text-4xl leading-tight sm:text-6xl">
        Play it.<br>Open it.<br>Program it.<br>Keep it.
      </h1>
      <p class="mb-7 max-w-[46ch] text-lg text-text-dim">
        Physical games, computers, electronic toys and programmable machines — built for an alternate technological future where you actually own what you buy.
      </p>
      <div class="flex flex-wrap gap-3">
        <RouterLink
          to="/shop"
          class="border border-brand bg-brand px-5 py-3 font-mono text-xs uppercase tracking-wide text-white transition-opacity hover:opacity-90"
        >
          Browse the catalog
        </RouterLink>
        <RouterLink
          to="/about"
          class="border border-border px-5 py-3 font-mono text-xs uppercase tracking-wide transition-colors hover:bg-bg-alt"
        >
          Read the brand map
        </RouterLink>
      </div>
      <p class="mt-9 font-mono text-xs tracking-[0.2em] text-text-dim">PLAY · BUILD · PROGRAM · KEEP</p>
    </div>
  </section>

  <section class="border-b border-border py-10">
    <div class="mx-auto max-w-6xl px-6">
      <div class="grid grid-cols-2 gap-px border border-border bg-border sm:grid-cols-5">
        <RouterLink
          v-for="c in catalog.categories"
          :key="c.id"
          :to="{ path: '/shop', query: { cat: c.id } }"
          class="flex flex-col gap-1 bg-bg p-5 transition-colors hover:bg-accent hover:text-accent-text"
        >
          <span class="font-mono text-[0.68rem] text-brand">{{ c.code }}</span>
          <span class="font-mono text-sm uppercase tracking-wide">{{ c.name }}</span>
        </RouterLink>
      </div>
    </div>
  </section>

  <section class="py-12">
    <div class="mx-auto max-w-6xl px-6">
      <div class="mb-6 flex items-baseline justify-between gap-4 border-b border-border pb-3">
        <h2 class="font-mono text-lg uppercase tracking-wide">New releases</h2>
        <RouterLink to="/shop" class="font-mono text-xs uppercase tracking-wide text-text-dim hover:text-brand">
          View full catalog →
        </RouterLink>
      </div>
      <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <ProductCard v-for="p in featured" :key="p.id" :product="p" />
      </div>
    </div>
  </section>
</template>
