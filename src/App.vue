<script setup>
import { onMounted, watch } from "vue";
import AppHeader from "./components/AppHeader.vue";
import AppFooter from "./components/AppFooter.vue";
import ThemeOverlay from "./components/ThemeOverlay.vue";
import Toast from "./components/Toast.vue";
import { useCatalogStore } from "./stores/catalog";
import { useTaglineStore } from "./stores/tagline";

const catalog = useCatalogStore();
const tagline = useTaglineStore();
onMounted(() => catalog.load());

// Keep <title>/og:title/twitter:title/og:image:alt in step with the same
// rotating line shown on the page. Note: og/twitter tags only matter to
// link-unfurl bots, which fetch the page cold with no JS — so they'll only
// ever see whatever line is baked into index.html at deploy time, not the
// live rotation. This just keeps the browser tab title (which *is* live)
// and the DOM meta tags consistent with what's on screen.
function syncDocumentMeta(text) {
  document.title = `RODDY — ${text}`;
  const setMeta = (selector, value) => {
    const el = document.querySelector(selector);
    if (el) el.setAttribute("content", value);
  };
  setMeta('meta[property="og:title"]', `RODDY — ${text}`);
  setMeta('meta[name="twitter:title"]', `RODDY — ${text}`);
  setMeta('meta[property="og:image:alt"]', `RODDY ● — ${text}`);
}

onMounted(() => {
  tagline.start();
  syncDocumentMeta(tagline.current);
});
watch(() => tagline.current, syncDocumentMeta);
</script>

<template>
  <AppHeader />
  <main class="flex-1">
    <RouterView />
  </main>
  <AppFooter />
  <ThemeOverlay />
  <Toast />
  <div class="crt-scanlines" />
</template>
