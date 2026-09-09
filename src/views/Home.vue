<script setup>
import { computed } from "vue";
import { useCatalogStore, productImageUrl } from "../stores/catalog";
import { useThemeStore } from "../stores/theme";
import { useUiStore } from "../stores/ui";
import ProductCard from "../components/ProductCard.vue";
import ProductArtwork from "../components/ProductArtwork.vue";
import RoddyLogo from "../components/RoddyLogo.vue";
const catalog = useCatalogStore();
const theme = useThemeStore();
const ui = useUiStore();
const settings = computed(() => catalog.settings);
const featured = computed(() =>
  catalog.products.filter((p) => p.featured && p.active),
);
const spotlight = computed(() => catalog.byId(settings.value.heroProductId));
const heroImage = computed(
  () => settings.value.heroImage || spotlight.value?.coverImage,
);
const divisions = computed(() =>
  catalog.categories.filter((c) => catalog.byCategory(c.id).length),
);
</script>
<template>
  <div class="world-announcement">
    <span class="status-dot" />{{ settings.announcement
    }}<span class="hidden sm:inline">EST. IN ANOTHER TIMELINE ↗</span>
  </div>
  <section class="world-hero">
    <div class="hero-copy">
      <p class="eyebrow">
        <span class="status-dot" /> {{ settings.heroEyebrow }}
      </p>
      <h1>{{ settings.heroTitle }}</h1>
      <p class="hero-description">{{ settings.heroDescription }}</p>
      <div class="hero-actions">
        <RouterLink to="/shop" class="button primary"
          >{{ settings.heroButton }} <span>↗</span></RouterLink
        ><button class="text-button" @click="ui.openThemeOverlay()">
          ◧ Find your color
        </button>
      </div>
      <div class="hero-footnote">
        <span>PLAY. BUILD. PROGRAM. KEEP.</span><span>● RODDY WORLD / 01</span>
      </div>
    </div>
    <RouterLink
      v-if="spotlight"
      :to="`/product/${spotlight.id}`"
      class="hero-exhibit"
      :aria-label="`Discover ${spotlight.name}`"
    >
      <div class="exhibit-top">
        <span>THE NEXT LITTLE BIG THING</span
        ><span
          >{{
            spotlight.status === "coming-soon"
              ? "IN DEVELOPMENT"
              : "IN THE SPOTLIGHT"
          }}
          ●</span
        >
      </div>
      <div class="orbital-ring ring-one" />
      <div class="orbital-ring ring-two" />
      <img
        v-if="heroImage"
        :src="productImageUrl(heroImage)"
        :alt="spotlight.name"
        class="hero-product-image"
        fetchpriority="high"
      />
      <ProductArtwork v-else :product="spotlight" />
      <span class="exhibit-sticker"
        >{{
          spotlight.status === "coming-soon"
            ? "COMING\nSOON"
            : "MEET YOUR\nNEXT IDEA"
        }}
        <span>↗</span></span
      >
      <div class="exhibit-bottom">
        <div>
          <small>{{ spotlight.category }} DIVISION / {{ spotlight.sku }}</small>
          <h2>{{ spotlight.name }}</h2>
        </div>
        <span class="exhibit-arrow">↗</span>
      </div>
    </RouterLink>
    <div v-else class="hero-exhibit hero-empty">
      <RoddyLogo kind="full_logo" class="hero-fallback-logo" />
      <p>PERSONAL TECHNOLOGY. UNIVERSAL POSSIBILITIES.</p>
    </div>
  </section>
  <div class="spectrum-band" aria-hidden="true">
    <i v-for="n in 6" :key="n" />
  </div>
  <section class="division-strip">
    <RouterLink
      v-for="(c, i) in divisions"
      :key="c.id"
      :to="{ path: '/shop', query: { cat: c.id } }"
      ><small>0{{ i + 1 }} / {{ c.code }}</small
      ><span>{{ c.name }} <b>↗</b></span></RouterLink
    >
  </section>
  <section class="world-catalog">
    <div class="section-heading">
      <div>
        <p class="eyebrow">THE RODDY LINEUP</p>
        <h2>{{ settings.featuredTitle }}</h2>
      </div>
      <RouterLink to="/shop" class="text-button">All departments ↗</RouterLink>
    </div>
    <div class="catalog-grid">
      <ProductCard v-for="p in featured" :key="p.id" :product="p" />
    </div>
  </section>
  <section class="world-manifesto">
    <div>
      <p class="eyebrow">A NOTE FROM THE DEPARTMENT OF POSSIBILITY</p>
      <h2>{{ settings.manifestoTitle }}</h2>
      <p>{{ settings.manifestoText }}</p>
      <RouterLink to="/about" class="button">Meet RODDY ↗</RouterLink>
    </div>
    <div class="possibility-art" aria-hidden="true">
      <span class="orbit orbit-a" /><span class="orbit orbit-b" /><span
        class="orbit orbit-c"
      />
      <RoddyLogo kind="badge" on-accent class="possibility-logo" />
      <small>HUMAN CURIOSITY / ALWAYS COMPATIBLE</small>
    </div>
  </section>
  <section class="world-themes">
    <div>
      <p class="eyebrow">SAME WORLD. DIFFERENT FREQUENCY.</p>
      <h2>MAKE YOURSELF AT HOME.</h2>
      <p>
        Every corner of RODDY changes with your colorway. Find the one that
        feels like you.
      </p>
    </div>
    <div>
      <div class="theme-swatches">
        <button
          v-for="t in theme.themes"
          :key="t.id"
          :title="t.label || t.id"
          :aria-label="`Use ${t.label || t.id} theme`"
          :aria-pressed="theme.currentId === t.id"
          :style="{
            background:
              'linear-gradient(135deg, ' +
              t.swatch[0] +
              ' 50%, ' +
              t.swatch[1] +
              ' 50%)',
          }"
          @click="theme.apply(t.id)"
        >
          <span v-if="theme.currentId === t.id">●</span>
        </button>
      </div>
      <button class="text-button" @click="ui.openThemeOverlay()">
        ◧ Explore all {{ theme.themes.length }} colorways ↗
      </button>
    </div>
  </section>
</template>
