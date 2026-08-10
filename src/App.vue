<script setup>
import { onMounted } from "vue";
import AppHeader from "./components/AppHeader.vue";
import AppFooter from "./components/AppFooter.vue";
import ThemeOverlay from "./components/ThemeOverlay.vue";
import Toast from "./components/Toast.vue";
import { useCatalogStore } from "./stores/catalog";

const catalog = useCatalogStore();
onMounted(() => catalog.load());
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
