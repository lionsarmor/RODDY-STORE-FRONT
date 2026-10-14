<script setup>
import {ref,watch,onUnmounted} from 'vue';
import {commerceRequest} from './commerce-api';
const props=defineProps({endpoint:String,token:String,connected:Boolean,visible:Boolean});
const emit=defineEmits(['open-orders','new-sale','queue-update']);
const pending=ref(0),latest=ref(null),error=ref(''),enabled=ref(false),supported=typeof Notification!=='undefined',busy=ref(false);
let timer=null,cursor=null,loading=false,sequence=0;
const key=()=> 'roddy:sales-cursor:'+props.endpoint;
const enabledKey=()=> 'roddy:sales-alerts:'+props.endpoint;
const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);
async function poll(){
 if(!props.connected || loading)return;loading=true;const run=sequence;
 try{
  const result=await commerceRequest(props.endpoint,'/admin/sales'+(cursor===null?'':'?after='+cursor),props.token);
  if(run!==sequence)return;
  cursor=result.cursor;pending.value=result.pendingOrders ?? 0;emit('queue-update',pending.value);error.value='';
  try{localStorage.setItem(key(),String(cursor));}catch{}
  if(result.sales.length){emit('new-sale');latest.value=result.sales.at(-1);if(enabled.value&&supported&&Notification.permission==='granted'){
    const sale=result.sales.at(-1);const notification=new Notification(result.sales.length>1?`${result.sales.length} confirmed RODDY sales`:`RODDY sale · ${money(sale.amountCents)}`,{body:sale.items.map(i=>`${i.qty} × ${i.name}`).join(', '),tag:'roddy-sale-'+sale.id});
    notification.onclick=()=>{window.focus();emit('open-orders');notification.close();};
  }}
 }catch(e){if(run===sequence)error.value=e.message;}finally{loading=false;}
}
async function enable(){
 if(!supported)return;busy.value=true;
 try{const permission=await Notification.requestPermission();enabled.value=permission==='granted';try{localStorage.setItem(enabledKey(),enabled.value?'1':'0');}catch{}if(!enabled.value)error.value='Allow notifications in your browser site settings, then try again.';}finally{busy.value=false;}
}
function disable(){enabled.value=false;try{localStorage.setItem(enabledKey(),'0');}catch{}}
watch(()=>[props.connected,props.endpoint],()=>{
 sequence++;clearInterval(timer);timer=null;cursor=null;pending.value=0;emit('queue-update',0);latest.value=null;error.value='';
 if(props.connected){try{const saved=localStorage.getItem(key());if(saved!==null&&/^\d+$/.test(saved))cursor=Number(saved);enabled.value=supported&&Notification.permission==='granted'&&localStorage.getItem(enabledKey())==='1';}catch{}poll();timer=setInterval(poll,30000);}
},{immediate:true});
onUnmounted(()=>{sequence++;clearInterval(timer);});
</script>
<template>
  <details v-if="connected&&visible" class="sale-notifications" aria-label="Sale notification settings"><summary><span>◉ Sale notifications</span><b>{{enabled?'On for this device':'Set up alerts'}} <span aria-hidden="true">⌄</span></b></summary><div class="notification-settings"><p>Get an alert for any confirmed sale—keycaps, hardware, merchandise or downloads.</p><button v-if="supported&&!enabled" class="button small" :disabled="busy" @click="enable">Enable sale notifications on this device</button><button v-else-if="enabled" class="button small" @click="disable">Sale notifications on · turn off</button><p v-else>Browser notifications are unavailable here. Orders still refresh while admin is open.</p><p class="notification-note">Keep admin open and signed in for alerts, even while you use another tab. Your browser and operating system control whether they appear.</p><p v-if="latest" role="status">Latest sale: {{money(latest.amountCents)}} · {{latest.items.map(i=>i.name).join(', ')}}</p><p v-if="error" role="status" class="notification-note">{{error}}</p></div></details>
</template>
<style scoped>.sale-notifications{border:1px solid var(--color-border,#444);border-radius:12px;margin:0 0 24px;background:#93b0db08}.sale-notifications summary{display:flex;justify-content:space-between;align-items:center;gap:16px;cursor:pointer;padding:15px 18px;font-size:12px;list-style:none}.sale-notifications summary b{font:11px monospace;color:#93B0DB;display:flex;gap:12px}.notification-settings{padding:0 18px 18px}.notification-settings p{font-size:12px;line-height:1.7;margin-bottom:12px}.notification-note{opacity:.65}.notification-settings button{margin:4px 0 12px}@media(max-width:600px){.sale-notifications summary{align-items:flex-start;flex-direction:column;gap:8px}}</style>
