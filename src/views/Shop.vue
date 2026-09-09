<script setup>
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { useCatalogStore } from "../stores/catalog";
import ProductCard from "../components/ProductCard.vue";

const route = useRoute();
const catalog = useCatalogStore();

const activeCat = computed(() => route.query.cat || "all");
const search = ref("");
const tag = ref("");
const sort = ref("featured");
const list = computed(() => {
  const result = catalog
    .byCategory(activeCat.value)
    .filter(
      (p) =>
        `${p.name} ${p.description}`
          .toLowerCase()
          .includes(search.value.toLowerCase()) &&
        (!tag.value || p.tags.includes(tag.value)),
    );
  return result.sort((a, b) =>
    sort.value === "price-low"
      ? a.price - b.price
      : sort.value === "price-high"
        ? b.price - a.price
        : sort.value === "name"
          ? a.name.localeCompare(b.name)
          : Number(b.featured) - Number(a.featured),
  );
});
const chips = computed(() => [
  { id: "all", name: "All" },
  ...catalog.categories,
]);
</script>

<template>
  <div class="border-b border-border py-10">
    <div class="mx-auto max-w-6xl px-6">
      <h1 class="mb-2 font-mono text-3xl uppercase tracking-wide">Catalog</h1>
      <p class="max-w-[60ch] text-text-dim">
        Explore the RODDY departments. Find your next little obsession, or see
        what is taking shape in the lab.
      </p>
    </div>
  </div>
  <section class="py-12">
    <div class="mx-auto max-w-6xl px-6">
      <div class="mb-7 flex flex-wrap gap-2">
        <RouterLink
          v-for="c in chips"
          :key="c.id"
          :to="
            c.id === 'all' ? '/shop' : { path: '/shop', query: { cat: c.id } }
          "
          class="border border-border px-4 py-2 font-mono text-xs uppercase tracking-wide text-text-dim transition-colors hover:text-text"
          :class="
            activeCat === c.id
              ? 'border-accent! bg-accent text-accent-text!'
              : ''
          "
        >
          {{ c.name }}
        </RouterLink>
      </div>
      <div class="catalog-filters">
        <label
          >Find something<input
            v-model="search"
            type="search"
            placeholder="Search the catalog…" /></label
        ><label
          >Tag<select v-model="tag">
            <option value="">All tags</option>
            <option v-for="t in catalog.tags" :key="t.id" :value="t.id">
              {{ t.label }}
            </option>
          </select></label
        ><label
          >Sort<select v-model="sort">
            <option value="featured">Featured first</option>
            <option value="price-low">Price: low to high</option>
            <option value="price-high">Price: high to low</option>
            <option value="name">Name</option>
          </select></label
        >
      </div>
      <div v-if="list.length" class="catalog-grid">
        <ProductCard v-for="p in list" :key="p.id" :product="p" />
      </div>
      <div
        v-else
        class="border border-dashed border-border p-12 text-center font-mono text-text-dim"
      >
        Nothing in this category yet. Check back soon.
      </div>
    </div>
  </section>
</template>
