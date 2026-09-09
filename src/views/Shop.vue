<script setup>
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import {
  useCatalogStore,
  stockState,
  formatPrice,
  productImageUrl,
} from "../stores/catalog";
import { departmentDirection } from "../department-data";
import ProductCard from "../components/ProductCard.vue";
import ProductArtwork from "../components/ProductArtwork.vue";
import ProductTags from "../components/ProductTags.vue";
import RoddyLogo from "../components/RoddyLogo.vue";

const route = useRoute();
const catalog = useCatalogStore();
const activeCat = computed(() =>
  typeof route.query.cat === "string" ? route.query.cat : "all",
);
const direction = computed(() => departmentDirection(activeCat.value));
const category = computed(() => catalog.categoryMeta(activeCat.value));
const search = ref("");
const tag = ref("");
const sort = ref("featured");
const filtered = computed(() => Boolean(search.value.trim() || tag.value));
const list = computed(() => {
  const result = catalog
    .byCategory(activeCat.value)
    .filter(
      (p) =>
        `${p.name} ${p.description}`
          .toLowerCase()
          .includes(search.value.trim().toLowerCase()) &&
        (!tag.value || p.tags.includes(tag.value)),
    );
  return result.sort((a, b) => {
    if (sort.value.startsWith("price-")) {
      // Unannounced prices are not $0 offers; keep them behind known prices.
      if (Boolean(a.pricePending) !== Boolean(b.pricePending))
        return a.pricePending ? 1 : -1;
      return sort.value === "price-low" ? a.price - b.price : b.price - a.price;
    }
    return sort.value === "name"
      ? a.name.localeCompare(b.name)
      : Number(b.featured) - Number(a.featured);
  });
});
const chips = computed(() => [
  { id: "all", name: "All departments" },
  ...catalog.categories,
]);
const spotlight = computed(() =>
  activeCat.value === "all" && !filtered.value
    ? catalog.byId(catalog.settings.heroProductId)
    : null,
);
const spotlightImage = computed(
  () => spotlight.value?.coverImage || spotlight.value?.images?.[0],
);
function clearFilters() {
  search.value = "";
  tag.value = "";
  sort.value = "featured";
}
</script>

<template>
  <div class="shop-directory" :data-motif="direction.motif">
    <header class="directory-masthead">
      <div class="publication-line">
        <span>RODDY / {{ direction.label }}</span
        ><span>INDEPENDENT TECHNOLOGY / UNREASONABLE POSSIBILITIES</span>
      </div>
      <div class="directory-cover">
        <div class="directory-cover-copy">
          <p class="eyebrow">
            <span class="status-dot" />{{
              category?.name || "The RODDY catalog"
            }}
            / {{ category?.code || "Find your next little obsession" }}
          </p>
          <h1>{{ direction.title }}</h1>
          <p class="directory-intro">{{ direction.note }}</p>
        </div>
        <div class="directory-seal" aria-hidden="true">
          <span class="seal-coordinate">PERSONAL TECHNOLOGY / 01</span>
          <div class="seal-orbits"><RoddyLogo kind="badge" /></div>
          <span class="seal-caption"
            >PLAY IT. OPEN IT.<br />PROGRAM IT. KEEP IT.</span
          >
          <span class="seal-cross">+</span>
        </div>
      </div>
      <div class="directory-edition">
        <span>A CATALOG FROM ANOTHER TIMELINE</span
        ><span>HUMAN CURIOSITY: ALWAYS COMPATIBLE ↗</span>
      </div>
    </header>

    <section class="directory-content" aria-label="Product catalog">
      <nav class="department-tabs" aria-label="Shop departments">
        <RouterLink
          v-for="(c, i) in chips"
          :key="c.id"
          :to="
            c.id === 'all' ? '/shop' : { path: '/shop', query: { cat: c.id } }
          "
          :aria-current="activeCat === c.id ? 'page' : undefined"
        >
          <small>{{ String(i).padStart(2, "0") }}</small
          ><span>{{ c.name }}</span>
          <span class="department-count">{{
            catalog.byCategory(c.id).length
          }}</span>
        </RouterLink>
      </nav>

      <section
        v-if="spotlight"
        class="catalog-spotlight"
        aria-labelledby="spotlight-title"
        :class="{ 'is-development': stockState(spotlight) === 'soon' }"
      >
        <RouterLink
          :to="`/product/${spotlight.id}`"
          class="spotlight-art"
          :aria-label="`Explore ${spotlight.name}`"
        >
          <div class="plate-annotation">
            <span>{{ spotlight.sku }}</span
            ><span>FEATURED EXHIBIT / 01</span>
          </div>
          <img
            v-if="spotlightImage"
            :src="productImageUrl(spotlightImage)"
            :alt="spotlight.name"
            fetchpriority="high"
          />
          <ProductArtwork v-else :product="spotlight" />
          <div class="plate-annotation">
            <span
              >{{
                catalog.categoryMeta(spotlight.category)?.name
              }}
              DIVISION</span
            ><span>↗</span>
          </div>
        </RouterLink>
        <div class="spotlight-copy">
          <p class="eyebrow">
            <span class="status-dot" />{{
              stockState(spotlight) === "soon"
                ? "From the workbench / Coming soon"
                : "In the RODDY spotlight"
            }}
          </p>
          <h2 id="spotlight-title">{{ spotlight.name }}</h2>
          <p>{{ spotlight.shortDescription || spotlight.description }}</p>
          <ProductTags :ids="spotlight.tags" />
          <div class="spotlight-action">
            <RouterLink :to="`/product/${spotlight.id}`" class="button primary"
              >{{
                stockState(spotlight) === "soon"
                  ? "Explore the project"
                  : "Meet your next idea"
              }}
              ↗</RouterLink
            >
            <span class="eyebrow">{{
              stockState(spotlight) === "soon"
                ? "IN DEVELOPMENT · NOT YET FOR SALE"
                : stockState(spotlight) === "out"
                  ? "CURRENTLY SOLD OUT"
                  : spotlight.pricePending
                    ? "PRICING TO BE ANNOUNCED"
                    : spotlight.price === 0
                      ? "FREE TO EXPLORE"
                      : formatPrice(spotlight.price) + " USD"
            }}</span>
          </div>
        </div>
      </section>

      <div class="directory-list-heading">
        <div>
          <p class="eyebrow">BROWSE THE INVENTORY</p>
          <h2>
            {{ category?.name || "The whole curious collection"
            }}<span> /</span>
          </h2>
        </div>
        <p aria-live="polite">
          {{ list.length }} {{ list.length === 1 ? "ENTRY" : "ENTRIES"
          }}<br />YOURS TO DISCOVER
        </p>
      </div>
      <div class="catalog-filters">
        <label
          >01 / Find something<input
            v-model="search"
            type="search"
            placeholder="Search the catalog…"
        /></label>
        <label
          >02 / Filter by tag<select v-model="tag">
            <option value="">All tags</option>
            <option v-for="t in catalog.tags" :key="t.id" :value="t.id">
              {{ t.label }}
            </option>
          </select></label
        >
        <label
          >03 / Sort the shelf<select v-model="sort">
            <option value="featured">Featured first</option>
            <option value="price-low">Price: low to high</option>
            <option value="price-high">Price: high to low</option>
            <option value="name">Name</option>
          </select></label
        >
      </div>
      <div v-if="filtered" class="filter-summary">
        <span>Filtered collection · {{ list.length }} results</span
        ><button class="text-button" @click="clearFilters">
          Clear filters ×
        </button>
      </div>
      <div v-if="!catalog.loaded" class="directory-empty" role="status">
        <h3>
          {{
            catalog.error
              ? "THE SHELF IS TEMPORARILY OFFLINE."
              : "OPENING THE DIRECTORY…"
          }}
        </h3>
        <p>{{ catalog.error || "A few good things are on their way." }}</p>
        <button v-if="catalog.error" class="button" @click="catalog.load()">
          Try again ↗
        </button>
      </div>
      <div v-else-if="list.length" class="catalog-grid">
        <ProductCard v-for="p in list" :key="p.id" :product="p" />
      </div>
      <div v-else class="directory-empty">
        <p class="eyebrow">ROOM FOR POSSIBILITY</p>
        <h3>
          {{
            filtered
              ? "NOTHING ON THIS FREQUENCY."
              : "THIS SHELF IS STILL TAKING SHAPE."
          }}
        </h3>
        <p>
          {{
            filtered
              ? "Try a different search or remove a filter."
              : "No products here yet. There is plenty to discover in the other departments."
          }}
        </p>
        <button v-if="filtered" class="button" @click="clearFilters">
          Clear filters ↗</button
        ><RouterLink v-else to="/shop" class="button"
          >All departments ↗</RouterLink
        >
      </div>

      <aside class="catalog-colophon">
        <RoddyLogo kind="badge" />
        <div>
          <p class="eyebrow">A NOTE FROM THE MAKERS</p>
          <h2>LESS DISPOSABLE.<br />MORE DISCOVERABLE.</h2>
          <p>
            We like technology you can get to know. Curious ideas, human-scale
            machines, and a future with room for you in it.
          </p>
        </div>
        <RouterLink to="/about" class="text-button">The RODDY way ↗</RouterLink>
      </aside>
    </section>
  </div>
</template>
