<script setup>
import {computed,onMounted,ref} from 'vue';
import {commerceRequest} from './commerce-api.js';
const props=defineProps({product:Object,endpoint:String,token:String});
const settings=ref(null),prices=ref([]),busy=ref(false),error=ref('');
const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);
const rows=computed(()=>prices.value.filter(r=>r.id===props.product.id&&r.revision===settings.value?.revision&&r.checkedAt>Date.now()/1000-3600));
async function load(){busy.value=true;error.value='';try{const data=await commerceRequest(props.endpoint,'/admin/pricing',props.token);settings.value=data.settings;prices.value=data.prices;}catch(e){error.value=e.message;}finally{busy.value=false;}}
onMounted(load);
</script>
<template>
  <section class="live-product-price" aria-label="Live automatic pricing">
    <h3>Live automatic pricing</h3>
    <p v-if="settings&&!settings.enabled">Automatic pricing is switched off. The base / fallback price below applies.</p>
    <template v-else-if="settings"><p>{{settings.markupPercent}}% markup on supplier goods, shipping, tax and fees · payment fee reserve {{settings.feePercent}}% + {{money(settings.feeFixed*100)}}</p>
      <div v-for="row in rows" :key="row.variantId" class="live-price-row"><strong>{{row.available&&row.priceCents?money(row.priceCents)+' + quoted shipping':'Supplier price needs review'}}<small v-if="row.variantId"> · variant {{row.variantId}}</small></strong><p v-if="row.landedCents!=null">Supplier cost basis {{money(row.landedCents)}}<span v-if="row.shippingCents!=null">, including {{money(row.shippingCents)}} shipping</span>. Shipping is shown separately at checkout and is not charged twice.</p><p>Checked {{new Date(row.checkedAt*1000).toLocaleString()}}</p><p v-if="row.error" class="notice">{{row.error}}</p></div>
      <p v-if="!rows.length">A current price estimate is not available yet. Check Suppliers → Automatic pricing.</p>
      <p>The price below is the catalog fallback. Delivery-address quotes confirm the final current price before payment.</p>
    </template>
    <p v-if="error" role="alert" class="notice">{{error}}</p><button type="button" class="button small" :disabled="busy" @click="load">{{busy?'Loading price…':'Refresh live price'}}</button>
  </section>
</template>
<style scoped>
.live-product-price{padding:20px;margin-bottom:24px;border:1px solid #93b0db66;border-radius:12px;background:#93b0db0c}.live-product-price h3{font-size:18px;font-weight:800;margin-bottom:12px}.live-product-price p{font-size:12px;line-height:1.7;margin:10px 0}.live-price-row{margin:16px 0;padding:14px;border-left:3px solid #8DD1AE;background:#8dd1ae08}.live-price-row>strong{font-size:22px}.live-price-row small{font-size:11px}.live-product-price button{margin-top:8px}
</style>
