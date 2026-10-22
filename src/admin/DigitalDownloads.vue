<script setup>
import {computed,reactive,ref} from 'vue';
import {commerceRequest} from './commerce-api.js';
import {downloadDestination} from '../checkout-links.js';
import {digitalDownloadDraft,mailtoDraft} from './order-mail.js';

const props=defineProps({order:Object,endpoint:String,token:String,disabled:Boolean});
const items=computed(()=>props.order.items.filter(i=>['digital','free-digital'].includes(i.kind)));
const busy=ref(''),error=ref(''),feedback=ref(''),links=reactive({});
const expiry=value=>new Date(value*1000).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'});
async function issue(item,purpose){
  const link=await commerceRequest(props.endpoint,'/admin/orders/'+encodeURIComponent(props.order.id)+'/downloads',props.token,{productId:item.id,purpose});
  const url=downloadDestination(link.url,props.endpoint);
  if(!url || !Number.isFinite(link.expiresAt) || link.expiresAt*1000<=Date.now())throw new Error('The download link is invalid or expired. Please try again.');
  return {...link,url};
}
async function download(item){
  busy.value=item.id;error.value='';feedback.value='';
  try{
    const link=await issue(item,item.kind==='free-digital'?'share':'download');
    if(item.kind==='free-digital'){
      const a=document.createElement('a');a.href=link.url;a.target='_blank';a.rel='noopener noreferrer';a.click();
      links[item.id]=link;feedback.value='Download opened. Your link is also available below.';return;
    }
    const response=await fetch(link.url,{cache:'no-store',referrerPolicy:'no-referrer'});
    if(!response.ok){const data=await response.json().catch(()=>({}));throw new Error(data.error || 'The download could not start. Please try again.');}
    const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');
    a.href=url;a.download=link.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    feedback.value=item.name+' download started.';
  }catch(e){error.value=e.message;}finally{busy.value='';}
}
async function share(item){
  busy.value=item.id;error.value='';feedback.value='';
  try{links[item.id]=await issue(item,'share');feedback.value='Customer link ready. Copy it into your reply or open an email draft.';}
  catch(e){error.value=e.message;}finally{busy.value='';}
}
async function copy(item){
  error.value='';feedback.value='';
  if(links[item.id].expiresAt*1000<=Date.now()){error.value='This link has expired. Create a new customer link.';return;}
  try{await navigator.clipboard.writeText(links[item.id].url);feedback.value='Customer link copied. Paste it into your email reply.';}
  catch{error.value='Clipboard unavailable. Select and copy the link above.';}
}
function email(item){
  return mailtoDraft(digitalDownloadDraft(props.order,item,links[item.id],props.endpoint),{allowEmptyRecipient:true});
}
</script>
<template>
  <section class="digital-downloads" aria-label="Digital downloads">
    <p class="step-caption">DIGITAL DOWNLOADS</p><h3>Download or send it again.</h3>
    <p class="download-help">Download the purchased ZIP or create a private link for a customer reply. Customer links are valid for seven days.</p>
    <div v-for="item in items" :key="item.id" class="digital-file">
      <strong>{{item.name}}</strong>
      <div class="download-actions"><button class="button primary small" :disabled="disabled||!!busy" @click="download(item)">{{item.kind==='free-digital'?'Download file ↓':'Download ZIP ↓'}}</button><button class="button small" :disabled="disabled||!!busy" @click="share(item)">{{links[item.id]?'Create new customer link':'Create customer link'}}</button></div>
      <p v-if="busy===item.id" class="download-help" role="status">Checking payment and preparing your download…</p>
      <div v-if="links[item.id]" class="customer-download">
        <label :for="'download-'+order.id+'-'+item.id">Customer download link<input :id="'download-'+order.id+'-'+item.id" :value="links[item.id].url" readonly @focus="e=>e.target.select()" /></label>
        <p class="download-help">Expires {{expiry(links[item.id].expiresAt)}}</p>
        <a v-if="item.kind==='free-digital'" :href="links[item.id].url" target="_blank" rel="noopener noreferrer" class="button small">Open download ↗</a>
        <div class="download-actions"><button class="button small" :disabled="disabled||!!busy" @click="copy(item)">Copy link ⧉</button><a class="button small" :href="email(item) || undefined" @click="e=>{if(!email(item)||links[item.id].expiresAt*1000<=Date.now()){e.preventDefault();error='This link has expired or the email details are invalid. Create a new link.';}}">Open email draft ↗</a></div>
        <p class="download-help">{{order.address?.email?'Review and send from your email app.':'Add the customer’s email address in your email app.'}} Opening a draft does not send it.</p>
      </div>
    </div>
    <p v-if="feedback" class="download-feedback" role="status">{{feedback}}</p><p v-if="error" class="notice" role="alert">{{error}}</p>
  </section>
</template>
<style scoped>
.digital-downloads{border:1px solid #93b0db44;background:#93b0db08;border-radius:12px;padding:20px;margin-top:20px}.digital-downloads h3{font-size:18px;font-weight:800;margin-bottom:10px}.download-help{font-size:12px;line-height:1.7;opacity:.75;margin:8px 0}.digital-file{border-top:1px solid #93b0db33;padding-top:16px;margin-top:16px}.digital-file>strong{font-size:14px}.download-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}.customer-download{margin-top:16px}.customer-download label{display:grid;gap:8px;font-size:11px}.customer-download input{width:100%;min-width:0;border:1px solid var(--color-border,#555);background:var(--color-bg,#111318);color:inherit;border-radius:6px;padding:10px;font:11px monospace}.download-feedback{font-size:12px;color:#8DD1AE;margin-top:14px;line-height:1.7}
</style>
