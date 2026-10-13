<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { useUiStore } from '../stores/ui';
import { useCatalogStore } from '../stores/catalog';
import NewsletterSignup from './NewsletterSignup.vue';
const route = useRoute();
const ui = useUiStore();
const catalog = useCatalogStore();
const ready = ref(false);
const expanded = ref(false);
function joined() { dismissed.value = true; }
const dismissed = ref(false);
const overlayOpen = ref(false);
let timer;
const visible = computed(() => ready.value && !dismissed.value && !overlayOpen.value && !ui.themeOverlayOpen && catalog.loaded && !catalog.preview && !['cart', 'newsletter', 'contact'].includes(route.name));
function close() {
  dismissed.value = true;
  try { localStorage.setItem('roddy:newsletter:dismissedUntil', String(Date.now() + 30 * 86400000)); } catch { /* Stays dismissed for this visit. */ }
}
onMounted(() => {
  window.addEventListener('roddy:newsletter:joined', joined);
  try { dismissed.value = localStorage.getItem('roddy:newsletter:joined') === 'yes' || Number(localStorage.getItem('roddy:newsletter:dismissedUntil')) > Date.now(); } catch { /* Storage is optional. */ }
  timer = setTimeout(() => {
    overlayOpen.value = !!document.querySelector('dialog[open], [aria-modal="true"]');
    ready.value = true;
    // Avoid placing an invitation above an active dialog or theme selector.
    timer = setInterval(() => { overlayOpen.value = !!document.querySelector('dialog[open], [aria-modal="true"]'); }, 1000);
  }, 25000);
});
onBeforeUnmount(() => { clearTimeout(timer); clearInterval(timer); window.removeEventListener('roddy:newsletter:joined', joined); });
</script>
<template>
  <aside v-if="visible" class="newsletter-invite" aria-label="Occasional RODDY emails">
    <button class="invite-close" aria-label="Close newsletter invitation" @click="close">×</button>
    <p class="invite-eyebrow">A LITTLE SIGNAL. VERY OCCASIONALLY.</p>
    <h2>A tiny interruption. Sorry! 🙃</h2>
    <p>We got excited about new builds, odd ideas and occasional sales. Want a little RODDY in your inbox?</p>
    <button v-if="!expanded" class="invite-more" @click="expanded = true">I’m curious — sign me up</button>
    <NewsletterSignup v-else />
  </aside>
</template>
<style scoped>
.newsletter-invite{position:fixed;bottom:20px;right:20px;z-index:35;width:min(350px,calc(100vw - 32px));max-height:calc(100dvh - 40px);overflow-y:auto;padding:27px 22px 22px;border-radius:16px;border:1px solid #ccc3ad;background:linear-gradient(90deg,#f2627c,#eeb647,#75cfc5,#9d8ee9) top/100% 8px no-repeat,#fff8e9;color:#182023;box-shadow:0 10px 45px #0003}.invite-more{padding:11px 16px;border-radius:8px;background:#ae2349;color:white;font-size:14px;font-weight:bold}.invite-close{position:absolute;right:9px;top:12px;width:36px;height:36px;font-size:28px;line-height:1;border-radius:50%;background:#f1e6d5}.invite-eyebrow{font:10px monospace;letter-spacing:1px;max-width:240px}.newsletter-invite h2{font-size:23px;line-height:1.2;margin:13px 30px 12px 0}.newsletter-invite>p:not(.invite-eyebrow){font-size:14px;line-height:1.5;margin-bottom:18px}@media(max-width:500px){.newsletter-invite{right:16px;bottom:16px;width:min(320px,calc(100vw - 32px));padding:23px 18px 18px}}
</style>
