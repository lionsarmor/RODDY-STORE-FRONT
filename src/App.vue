<script setup>
import { onMounted, watch } from "vue";
import AppHeader from "./components/AppHeader.vue";
import AppFooter from "./components/AppFooter.vue";
import ThemeOverlay from "./components/ThemeOverlay.vue";
import NewsletterInvite from "./components/NewsletterInvite.vue";
import Toast from "./components/Toast.vue";
import { useCatalogStore } from "./stores/catalog";

const catalog = useCatalogStore();
onMounted(() => catalog.load());
watch(() => catalog.unlistedCategory, category => {
  let tag = document.querySelector('meta[data-unlisted-robots]');
  if (category && !tag) {
    tag = document.createElement('meta'); tag.name = 'robots';
    tag.dataset.unlistedRobots = ''; tag.content = 'noindex, nofollow';
    document.head.appendChild(tag);
  } else if (!category) tag?.remove();
});
const publicStoreUrl = import.meta.env.BASE_URL + '#/';

</script>

<template>
  <AppHeader />
  <div v-if="catalog.preview" class="notice preview-notice">DRAFT PREVIEW — these changes are not published. Checkout is disabled.</div>
  <div v-if="catalog.unlistedCategory && !catalog.preview" class="notice" role="status">Unlisted preview: {{ catalog.unlistedCategory.name }} · <a :href="publicStoreUrl">Return to public store</a></div>
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
