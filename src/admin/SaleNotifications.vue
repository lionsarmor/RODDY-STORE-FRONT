<script setup>
import {ref,watch,onUnmounted} from 'vue';
import {commerceRequest} from './commerce-api';
const props=defineProps({endpoint:String,token:String,connected:Boolean});
const emit=defineEmits(['open-orders','new-sale']);
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
  cursor=result.cursor;pending.value=result.pendingKeycaps;error.value='';
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
 sequence++;clearInterval(timer);timer=null;cursor=null;pending.value=0;latest.value=null;error.value='';
 if(props.connected){try{const saved=localStorage.getItem(key());if(saved!==null&&/^\d+$/.test(saved))cursor=Number(saved);enabled.value=supported&&Notification.permission==='granted'&&localStorage.getItem(enabledKey())==='1';}catch{}poll();timer=setInterval(poll,30000);}
},{immediate:true});
onUnmounted(()=>{sequence++;clearInterval(timer);});
</script>
<template>
  <aside v-if="connected" class="sale-notifications" aria-label="Sale notifications"><div><strong>{{pending}} new keycap {{pending===1?'order':'orders'}}</strong><p v-if="latest" role="status">Latest confirmed sale: {{money(latest.amountCents)}} · {{latest.items.map(i=>i.name).join(', ')}}</p><p v-else>Sales and the keycap queue refresh every 30 seconds while admin is open.</p></div><div class="admin-actions"><button class="button small" @click="$emit('open-orders')">Open orders ↗</button><button v-if="supported&&!enabled" class="button small" :disabled="busy" @click="enable">Enable sale notifications on this device</button><button v-else-if="enabled" class="button small" @click="disable">Sale notifications on · turn off</button></div><p v-if="enabled" class="notification-note">Keep this admin page open and signed in for browser alerts. Your browser and operating system control whether they appear. Orders stay saved when this page is closed.</p><p v-if="error" role="status" class="notification-note">{{error}}</p></aside>
</template>
<style scoped>.sale-notifications{display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap;border:1px solid var(--color-border,#444);border-left:4px solid #7FAFD3;padding:16px;margin:20px 0}.sale-notifications strong{font-size:14px}.sale-notifications p{font-size:11px;margin-top:6px}.notification-note{flex-basis:100%;opacity:.7}.sale-notifications .admin-actions{margin:0}</style>
