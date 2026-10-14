<script setup>
import {ref,onMounted,watch} from 'vue';
import {commerceRequest} from './commerce-api';
const props=defineProps({endpoint:String,token:String,connected:Boolean});
const customers=ref([]),search=ref(''),busy=ref(false),error=ref(''),more=ref(false);
async function load(append=false){if(!props.connected)return;busy.value=true;error.value='';try{const data=await commerceRequest(props.endpoint,'/admin/customers?search='+encodeURIComponent(search.value)+'&before='+(append?customers.value.at(-1)?.id || 0:0),props.token);customers.value=append?[...customers.value,...data.customers]:data.customers;more.value=data.hasMore;}catch(e){error.value=e.message;}finally{busy.value=false;}}
onMounted(()=>load());watch(()=>props.connected,ok=>{if(ok)load();else customers.value=[];});
</script>
<template>
  <section class="customer-desk"><header><p class="eyebrow">RODDY / THE PEOPLE BEHIND THE ORDERS</p><h2>YOUR CUSTOMERS.</h2><p>Account details and saved addresses, kept privately on your server. Guest delivery details remain with each order in Orders.</p></header>
    <form class="customer-search" @submit.prevent="load()"><input v-model="search" type="search" aria-label="Find customers" placeholder="Find a name, handle or email…" maxlength="160" /><button class="button" :disabled="busy || !connected">{{busy?'Loading…':'Find customers'}}</button></form><p v-if="error" class="error" role="alert">{{error}}</p><p v-if="!customers.length && !busy">No matching customer profiles yet.</p>
    <div class="customer-grid"><article v-for="person in customers" :key="person.id" class="customer-card"><h3>{{person.name || person.handle}}</h3><p>@{{person.handle}}</p><a v-if="person.email" :href="'mailto:'+person.email">{{person.email}}</a><details><summary>{{person.addresses.length}} saved address{{person.addresses.length===1?'':'es'}}</summary><div v-for="entry in person.addresses" :key="entry.id" class="customer-address"><strong>{{entry.label}}{{entry.default?' · default':''}}</strong><address>{{entry.address.first_name}} {{entry.address.last_name}}<br />{{entry.address.address1}}<template v-if="entry.address.address2"><br />{{entry.address.address2}}</template><br />{{entry.address.city}}, {{entry.address.region}} {{entry.address.zip}}<br />{{entry.address.country}}<br />{{entry.address.phone}}<br />{{entry.address.email}}</address></div></details></article></div>
    <button v-if="more" class="button" :disabled="busy" @click="load(true)">Load more</button>
  </section>
</template>
<style scoped>
.customer-desk header{border-bottom:3px solid var(--color-brand);padding-bottom:24px}.customer-desk h2{font-size:36px;font-weight:900;margin:16px 0}.customer-desk p{line-height:1.6}.customer-search{display:flex;gap:12px;margin:24px 0;flex-wrap:wrap}.customer-search input{flex:1;min-width:200px}.customer-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:20px}.customer-card{border:1px solid var(--color-border);padding:24px;border-radius:12px;overflow-wrap:anywhere}.customer-card h3{font-size:22px}.customer-card details{margin-top:20px}.customer-card summary{cursor:pointer}.customer-address{padding:16px 0;border-top:1px solid var(--color-border)}.customer-address address{font-style:normal;line-height:1.7;margin-top:8px}
</style>
