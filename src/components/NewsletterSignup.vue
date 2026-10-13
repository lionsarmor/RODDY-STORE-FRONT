<script setup>
import { ref } from 'vue';
import { useUiStore } from '../stores/ui';
import { useCatalogStore } from '../stores/catalog';
import { forumRequest } from '../forum-api';
defineProps({ variant: {type: String, default: 'standard'} });
const emit = defineEmits(['joined']);
const catalog = useCatalogStore();
const ui = useUiStore();
const email = ref('');
const consent = ref(false);
const company = ref('');
const busy = ref(false);
const error = ref('');
const message = ref('');
async function subscribe() {
  busy.value = true; error.value = '';
  try {
    if (catalog.preview) throw new Error('Newsletter signup is unavailable in draft preview.');
    const result = await forumRequest(catalog.settings.checkoutEndpoint, '/newsletter/subscribe', '', {email: email.value, consent: consent.value, company: company.value});
    message.value = result.message;
    try { localStorage.setItem('roddy:newsletter:joined', 'yes'); } catch { /* Private browsing. */ }
    ui.toast('Thanks! Newsletter signup saved.');
    window.dispatchEvent(new Event('roddy:newsletter:joined'));
    emit('joined');
  } catch (e) { error.value = e.message; }
  finally { busy.value = false; }
}
</script>
<template>
  <div class="newsletter-entry" :class="{'newsletter-entry-editorial': variant === 'editorial'}">
  <form v-if="!message" class="newsletter-signup" @submit.prevent="subscribe">
    <label>Email address<input v-model="email" type="email" autocomplete="email" maxlength="254" required placeholder="you@example.com" /></label>
    <label class="newsletter-consent"><input v-model="consent" type="checkbox" required /> <span>I want occasional RODDY email updates, new releases and offers. I can unsubscribe by replying to any newsletter.</span></label>
    <label class="newsletter-trap" aria-hidden="true">Company<input v-model="company" tabindex="-1" autocomplete="off" /></label>
    <button type="submit" :disabled="busy || !catalog.loaded">{{ busy ? 'Saving…' : 'Tune me in' }}</button>
    <p v-if="error" role="alert">{{ error }}</p>
  </form>
  <div v-else class="newsletter-confirmation" role="status"><strong v-if="variant === 'editorial'">SIGNAL RECEIVED.</strong><p>{{ message }}</p></div>
  </div>
</template>
<style scoped>
.newsletter-signup{display:grid;gap:14px}.newsletter-signup label:not(.newsletter-trap){display:grid;gap:6px;font-size:14px}.newsletter-signup input[type=email]{width:100%;min-width:0;padding:11px 12px;border:1px solid #8e8a83;border-radius:8px;background:white;color:#182023;font-size:16px}.newsletter-signup .newsletter-consent{display:flex!important;align-items:flex-start;gap:9px!important;font-size:12px!important;line-height:1.5}.newsletter-consent input{margin-top:4px;flex-shrink:0}.newsletter-signup button{padding:12px;border-radius:8px;background:#ae2349;color:white;font-weight:700}.newsletter-signup button:disabled{opacity:.6}.newsletter-trap{position:absolute;left:-10000px;width:1px;height:1px;overflow:hidden}.newsletter-signup p{font-size:13px;color:#982b30}
.newsletter-entry-editorial .newsletter-signup{gap:22px;}
.newsletter-entry-editorial .newsletter-signup label:not(.newsletter-trap){gap:10px;font-size:13px;font-weight:600;}
.newsletter-entry-editorial .newsletter-signup input[type=email]{padding:14px;border:1px solid var(--rule);border-radius:0;background:var(--color-bg);color:var(--color-text);font-family:var(--font-sans);}
.newsletter-entry-editorial .newsletter-signup input[type=email]::placeholder{color:var(--color-text-dim);opacity:.85;}
.newsletter-entry-editorial .newsletter-signup input:focus-visible{outline:2px solid var(--color-brand);outline-offset:3px;}
.newsletter-entry-editorial .newsletter-consent{color:var(--color-text-dim);font-weight:400!important;line-height:1.8!important;}
.newsletter-entry-editorial .newsletter-consent input{width:17px;height:17px;margin-top:3px;accent-color:var(--color-accent);}
.newsletter-entry-editorial .newsletter-signup button{min-height:48px;padding:14px 20px;border-radius:0;background:var(--color-accent);color:var(--color-accent-text);font:500 11px/1.6 var(--font-mono);text-transform:uppercase;letter-spacing:.05em;border:1px solid var(--color-text);}
.newsletter-entry-editorial .newsletter-signup p{color:var(--color-text);padding:14px;border:1px solid var(--color-brand);line-height:1.7;}
.newsletter-entry-editorial .newsletter-confirmation{padding:24px;border:1px solid var(--rule);background:var(--color-bg-alt);}
.newsletter-entry-editorial .newsletter-confirmation strong{display:block;font:700 19px/1.4 var(--font-mono);margin-bottom:14px;}
.newsletter-entry-editorial .newsletter-confirmation p{font-size:14px;line-height:1.9;}
</style>
