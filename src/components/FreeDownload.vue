<script setup>
import {ref,watch,onUnmounted} from 'vue';
import {useCatalogStore} from '../stores/catalog.js';
import {useCustomerStore} from '../stores/customer.js';
import {customerRequest} from '../customer-api.js';
import {downloadDestination} from '../checkout-links.js';
const props=defineProps({product:Object,url:String,editionId:String,label:{type:String,default:'Free download'},buttonClass:{type:String,default:'button primary'}});
const catalog=useCatalogStore(),customer=useCustomerStore();
const dialog=ref(null),email=ref(''),firstName=ref(''),consent=ref(false),company=ref(''),testerCode=ref(''),busy=ref(false),error=ref(''),ready=ref(null);
let requestId='',generation=0;
function open(){generation++;busy.value=false;email.value=customer.profile?.email || '';firstName.value=customer.profile?.name?.split(' ')[0] || '';consent.value=false;company.value='';testerCode.value='';error.value='';ready.value=null;requestId=crypto.randomUUID();dialog.value.showModal();}
watch(()=>[props.product.id,props.url,props.editionId],()=>{generation++;dialog.value?.close();ready.value=null;testerCode.value='';error.value='';busy.value=false;});
onUnmounted(()=>{generation++;});
async function prepare(){
  const current=generation,wantsUpdates=consent.value;
  busy.value=true;error.value='';
  try{
    if(catalog.preview)throw new Error('Download orders are unavailable in draft preview.');
    const result=await customerRequest(catalog.settings.checkoutEndpoint,'/free-downloads','',{requestId,productId:props.product.id,downloadUrl:props.url,editionId:props.editionId,testerCode:props.product.betaAccess?testerCode.value:undefined,email:email.value,firstName:firstName.value,newsletterConsent:wantsUpdates,company:company.value});
    const url=downloadDestination(result.url,catalog.settings.checkoutEndpoint);
    if(!url)throw new Error('The download link is invalid. Please try again.');
    if(wantsUpdates){try{localStorage.setItem('roddy:newsletter:joined','yes');}catch{}window.dispatchEvent(new Event('roddy:newsletter:joined'));}
    if(current!==generation)return;
    testerCode.value='';
    ready.value={...result,url};
  }catch(e){if(current===generation)error.value=e.message;}finally{if(current===generation)busy.value=false;}
}
</script>
<template>
  <button type="button" :class="buttonClass" @click="open"><slot>↓ {{label}}</slot></button>
  <dialog ref="dialog" class="free-download-dialog" :aria-label="'Free download: '+product.name" @cancel="e=>{if(busy)e.preventDefault()}">
    <header><div><p class="eyebrow">RODDY / {{product.betaAccess?'ALPHA TESTER ACCESS':'FREE DOWNLOAD'}}</p><h2>{{product.name}}</h2><p v-if="product.betaAccess">{{label}}</p></div><button type="button" aria-label="Close free download" :disabled="busy" @click="dialog.close()">×</button></header>
    <template v-if="ready"><p class="download-ready" role="status">Your $0 download order is ready.</p><p>{{label}}</p><a class="button primary" :href="ready.url" target="_blank" rel="noopener noreferrer">Download now ↓</a><p class="free-download-note">Order {{ready.orderReference}}<br />This link is valid for seven days. Need a hand? Contact support@roddy.world.</p></template>
    <form v-else @submit.prevent="prepare">
      <p v-if="product.betaAccess">Early build. Big ideas. A few rough edges. Enter your email and beta tester code to unlock this alpha download. No payment is needed.</p>
      <p v-else>This download is free. Add your email for the order record, then download here. No payment or account is needed.</p>
      <label>First name <small>optional</small><input v-model="firstName" autocomplete="given-name" maxlength="80" /></label>
      <label>Email address<input v-model="email" type="email" autocomplete="email" maxlength="254" required placeholder="you@example.com" /></label>
      <label v-if="product.betaAccess">Beta tester code<input v-model="testerCode" type="password" autocomplete="off" maxlength="120" required placeholder="Your invitation to the alpha" spellcheck="false" /></label>
      <label class="free-download-optin"><input v-model="consent" type="checkbox" /><span>I want occasional RODDY email updates, new releases and offers. I can unsubscribe by replying to any newsletter.</span></label>
      <label class="free-download-trap" aria-hidden="true">Company<input v-model="company" tabindex="-1" autocomplete="off" /></label>
      <button class="button primary" :disabled="busy">{{busy?'Preparing…':product.betaAccess?'Unlock alpha download ↓':'Get free download ↓'}}</button>
      <p class="free-download-note">Updates are optional. Your email is kept with this download for support and a thank-you.</p>
    </form>
    <p v-if="error" class="notice" role="alert">{{error}}</p>
  </dialog>
</template>
<style scoped>
.free-download-dialog{width:min(540px,calc(100% - 28px));max-height:calc(100dvh - 36px);overflow:auto;margin:auto;padding:28px;border:1px solid var(--color-border);border-top:4px solid var(--color-brand);border-radius:18px;background:var(--color-panel);color:var(--color-text)}.free-download-dialog::backdrop{background:#070b16bd;backdrop-filter:blur(5px)}header{display:flex;justify-content:space-between;gap:20px}header h2{font-size:24px;font-weight:800;line-height:1.2}header button{font-size:30px;align-self:start}form{display:grid;gap:18px;margin-top:20px}form>p,.download-ready{font-size:14px;line-height:1.7}form>label{display:grid;gap:7px;font-size:13px}input:not([type=checkbox]){width:100%;padding:11px;border:1px solid var(--color-border);border-radius:7px;color:inherit;background:var(--color-bg);font-size:16px}.free-download-optin{display:flex!important;align-items:flex-start;gap:10px!important;line-height:1.6;font-size:12px!important}.free-download-optin input{margin-top:3px;flex-shrink:0;accent-color:var(--color-brand)}.free-download-note{font-size:11px!important;line-height:1.7;opacity:.75;margin:12px 0}.free-download-trap{position:absolute;left:-10000px;width:1px;height:1px;overflow:hidden}.download-ready{margin:22px 0 12px}.download-ready~.button{margin-top:18px}small{font-size:11px;opacity:.7}
</style>
