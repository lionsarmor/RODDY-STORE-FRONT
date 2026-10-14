<script setup>
import { onMounted } from "vue";
import AppHeader from "./components/AppHeader.vue";
import AppFooter from "./components/AppFooter.vue";
import ThemeOverlay from "./components/ThemeOverlay.vue";
import NewsletterInvite from "./components/NewsletterInvite.vue";
import Toast from "./components/Toast.vue";
import { useCatalogStore } from "./stores/catalog";

const catalog = useCatalogStore();
onMounted(() => catalog.load());

</script>

<template>
  <AppHeader />
  <div v-if="catalog.preview" class="notice preview-notice">DRAFT PREVIEW — these changes are not published. Checkout is disabled.</div>
  <div v-if="catalog.error" class="notice" role="alert">{{ catalog.error }} <button class="text-button" @click="catalog.load()">Retry</button></div>
  <main class="flex-1">
    <RouterView />
  </main>
  <AppFooter />
  <ThemeOverlay />
  <Toast />
  <NewsletterInvite />
  <div class="crt-scanlines" />
</template>
