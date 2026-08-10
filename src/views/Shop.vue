<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useCatalogStore } from "../stores/catalog";
import ProductCard from "../components/ProductCard.vue";

const route = useRoute();
const catalog = useCatalogStore();

const activeCat = computed(() => route.query.cat || "all");
const list = computed(() => catalog.byCategory(activeCat.value));
const chips = computed(() => [{ id: "all", name: "All" }, ...catalog.categories]);
</script>

<template>
  <div class="border-b border-border py-10">
    <div class="mx-auto max-w-6xl px-6">
      <h1 class="mb-2 font-mono text-3xl uppercase tracking-wide">Catalog</h1>
      <p class="max-w-[60ch] text-text-dim">
        Every current release, machine and accessory. Stock counts are maintained by hand — a sold-out badge means exactly that.
      </p>
    </div>
  </div>
  <section class="py-12">
    <div class="mx-auto max-w-6xl px-6">
      <div class="mb-7 flex flex-wrap gap-2">
        <RouterLink
          v-for="c in chips"
          :key="c.id"
          :to="c.id === 'all' ? '/shop' : { path: '/shop', query: { cat: c.id } }"
          class="border border-border px-4 py-2 font-mono text-xs uppercase tracking-wide text-text-dim transition-colors hover:text-text"
          :class="activeCat === c.id ? 'border-accent! bg-accent text-accent-text!' : ''"
        >
          {{ c.name }}
        </RouterLink>
      </div>
      <div v-if="list.length" class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <ProductCard v-for="p in list" :key="p.id" :product="p" />
      </div>
      <div v-else class="border border-dashed border-border p-12 text-center font-mono text-text-dim">
        Nothing in this category yet. Check back soon.
      </div>
    </div>
  </section>
</template>
