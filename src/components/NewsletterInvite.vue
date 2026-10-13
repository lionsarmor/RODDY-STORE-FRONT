<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useCatalogStore } from '../stores/catalog';
import NewsletterSignup from './NewsletterSignup.vue';
const catalog = useCatalogStore();
const JOINED_KEY = 'roddy:newsletter:joined';
function alreadyJoined() {
  try { return localStorage.getItem(JOINED_KEY) === 'yes'; } catch { return false; }
}
const subscribed = ref(alreadyJoined());
const expanded = ref(false);
const dismissed = ref(false);
function joined() { subscribed.value = true; }
function syncJoined(event) {
  if (event.key === JOINED_KEY || event.key === null) subscribed.value = alreadyJoined();
}
const visible = computed(() => !subscribed.value && !dismissed.value && !catalog.preview);
// X closes this page visit only. Successful signup hides it on future visits.
function close() { dismissed.value = true; }
onMounted(() => {
  window.addEventListener('roddy:newsletter:joined', joined);
  window.addEventListener('storage', syncJoined);
  // Remove the old 30-day close preference without changing an existing signup.
  try { localStorage.removeItem('roddy:newsletter:dismissedUntil'); } catch { /* Storage is optional. */ }
});
onBeforeUnmount(() => {
  window.removeEventListener('roddy:newsletter:joined', joined);
  window.removeEventListener('storage', syncJoined);
});
</script>
<template>
  <aside v-if="visible" class="newsletter-invite" aria-label="Occasional RODDY emails">
    <button class="invite-close" aria-label="Close newsletter invitation" @click="close">×</button>
    <p class="invite-eyebrow">A LITTLE SIGNAL. VERY OCCASIONALLY.</p>
    <h2>A tiny interruption. Sorry! 🙃</h2>
    <p>Tune in for fresh signals from the workbench: retro hardware, new builds and the occasional shop special. Low frequency. High curiosity.</p>
    <button v-if="!expanded" class="invite-more" @click="expanded = true">I’m curious — sign me up</button>
    <NewsletterSignup v-else />
  </aside>
</template>
<style scoped>
.newsletter-invite{position:fixed;bottom:20px;right:20px;z-index:35;width:min(350px,calc(100vw - 32px));max-height:calc(100dvh - 40px);overflow-y:auto;padding:27px 22px 22px;border-radius:16px;border:1px solid #ccc3ad;background:linear-gradient(90deg,#f2627c,#eeb647,#75cfc5,#9d8ee9) top/100% 8px no-repeat,#fff8e9;color:#182023;box-shadow:0 10px 45px #0003}.invite-more{padding:11px 16px;border-radius:8px;background:#ae2349;color:white;font-size:14px;font-weight:bold}.invite-close{position:absolute;right:9px;top:12px;width:36px;height:36px;font-size:28px;line-height:1;border-radius:50%;background:#f1e6d5}.invite-eyebrow{font:10px monospace;letter-spacing:1px;max-width:240px}.newsletter-invite h2{font-size:23px;line-height:1.2;margin:13px 30px 12px 0}.newsletter-invite>p:not(.invite-eyebrow){font-size:14px;line-height:1.5;margin-bottom:18px}@media(max-width:500px){.newsletter-invite{right:16px;bottom:16px;width:min(320px,calc(100vw - 32px));padding:23px 18px 18px}}
</style>
