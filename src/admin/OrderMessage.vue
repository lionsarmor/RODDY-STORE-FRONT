<script setup>
import {ref,computed,nextTick} from 'vue';
import {thankYouDraft,mailtoDraft,customerShipments} from './order-mail.js';
import {commerceRequest} from './commerce-api.js';
const props=defineProps({endpoint:String,token:String});
const emit=defineEmits(['recorded']);
const dialog=ref(null),order=ref(null),draft=ref(null),confirmed=ref(false),busy=ref(false),error=ref(''),feedback=ref('');
const mailto=computed(()=>draft.value?mailtoDraft(draft.value):'');
async function open(value){order.value=value;draft.value=thankYouDraft(value);confirmed.value=false;error.value='';feedback.value='';await nextTick();dialog.value.showModal();}
async function copy(){try{await navigator.clipboard.writeText(`To: ${draft.value.recipient}\nSubject: ${draft.value.subject}\n\n${draft.value.body}`);feedback.value='Copied. Paste this into Proton Mail or your preferred email app.';}catch{error.value='Clipboard unavailable. Select and copy the message below.';}}
async function record(){busy.value=true;error.value='';try{await commerceRequest(props.endpoint,'/admin/orders/'+order.value.id+'/messages',props.token,{subject:draft.value.subject,body:draft.value.body,context:order.value.messageContext,confirmedSent:confirmed.value});emit('recorded');dialog.value.close();}catch(e){error.value=e.message;}finally{busy.value=false;}}
defineExpose({open});
</script>
<template>
  <dialog ref="dialog" class="message-dialog" aria-labelledby="message-title" @cancel="e=>{if(busy)e.preventDefault()}" @click="e=>{if(e.target===dialog&&!busy)dialog.close()}">
    <template v-if="draft"><header><div><p class="message-eyebrow">04 / THE PERSONAL TOUCH</p><h2 id="message-title">A little thanks.<br /><span>A great send-off.</span></h2></div><button class="close-message" type="button" aria-label="Close customer message" :disabled="busy" @click="dialog.close()">×</button></header>
      <p class="message-intro">{{customerShipments(order).length?'Your saved tracking details are already included.':'A ready-written thank-you for your customer.'}} Review it, open your email app, and send when you’re happy.</p>
      <label>To<input :value="draft.recipient" readonly /></label><label>Subject<input v-model="draft.subject" maxlength="200" /></label><label>Message<textarea v-model="draft.body" rows="13" maxlength="20000" /></label>
      <div class="message-actions"><a class="button primary" :href="mailto || undefined" :aria-disabled="!mailto" @click="e=>{if(!mailto)e.preventDefault()}">Open email draft ↗</a><button class="button" type="button" @click="copy">Copy message ⧉</button></div><p class="message-note">Send from your RODDY email address. Opening a draft does not send it.</p>
      <p v-if="feedback" role="status" class="message-feedback">{{feedback}}</p><p v-if="error" role="alert" class="notice">{{error}}</p>
      <footer><label class="sent-confirmation"><input v-model="confirmed" type="checkbox" />I sent this message from my email account.</label><button class="button primary" type="button" :disabled="busy||!confirmed||!draft.subject.trim()||!draft.body.trim()||!mailto" @click="record">{{busy?'Saving…':'Mark thank-you sent ✓'}}</button><p>Saved with this order so you can see who you’ve contacted.</p></footer>
    </template>
  </dialog>
</template>
<style scoped>
.message-dialog{width:min(720px,calc(100% - 28px));max-height:calc(100dvh - 36px);overflow:auto;margin:auto;padding:clamp(20px,4vw,36px);border:1px solid var(--color-border,#555);border-top:5px solid #F06434;border-radius:20px;background:var(--color-panel,#17191f);color:var(--color-text,#eee)}.message-dialog::backdrop{background:#070b16c9;backdrop-filter:blur(6px)}header{display:flex;justify-content:space-between;gap:20px}.message-eyebrow{font:11px monospace;letter-spacing:2px;margin-bottom:12px}h2{font-size:clamp(29px,5vw,42px);font-weight:900;line-height:1.08;margin:0}h2 span{color:#F06434}.close-message{align-self:start;font-size:32px;line-height:1;padding:0 5px}.message-intro{font-size:13px;line-height:1.7;opacity:.8;margin:22px 0}.message-dialog>label{display:grid;gap:7px;font-size:12px;margin:16px 0}.message-dialog input:not([type=checkbox]),textarea{width:100%;background:var(--color-bg,#111318);border:1px solid var(--color-border,#555);border-radius:8px;padding:11px;color:inherit;font:inherit}textarea{font-size:13px;line-height:1.65;resize:vertical}.message-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}.message-note,footer p{font-size:11px;opacity:.7;line-height:1.65;margin-top:12px}.message-feedback{font-size:12px;color:#79bd89;margin-top:12px}footer{border-top:1px solid var(--color-border,#555);padding-top:20px;margin-top:24px}.sent-confirmation{display:flex;align-items:center;gap:10px;font-size:12px;margin-bottom:16px}input[type=checkbox]{accent-color:#93B0DB;width:17px;height:17px;flex-shrink:0}
</style>
