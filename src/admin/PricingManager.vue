<script setup>
import {ref,onMounted} from 'vue';
import {commerceRequest} from './commerce-api';
const props=defineProps({endpoint:String,token:String,catalog:Object});
const settings=ref(null),prices=ref([]),busy=ref(false),error=ref(''),message=ref('');
const money=n=>n==null?'Unavailable':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);
const name=id=>props.catalog?.products.find(p=>p.id===id)?.name || id;
async function load(){try{const data=await commerceRequest(props.endpoint,'/admin/pricing',props.token);settings.value=data.settings;prices.value=data.prices;}catch(e){error.value=e.message;}}
async function save(){busy.value=true;error.value='';message.value='';try{const data=await commerceRequest(props.endpoint,'/admin/pricing',props.token,settings.value);settings.value=data.settings;prices.value=[];message.value='Pricing rules saved. Live prices refresh in the background; paid orders keep their original totals.';}catch(e){error.value=e.message;}finally{busy.value=false;}}
onMounted(load);
</script>
<template>
<section class="admin-section"><h2>Automatic pricing</h2><p>One markup rule for automatic fulfillment. Prices follow landed supplier costs and stock; checkout confirms prices and shipping for the customer’s address. Paid orders stay at their accepted price.</p>
<p v-if="error" class="notice">{{error}}</p><p v-if="message" class="notice">{{message}}</p>
<form v-if="settings" @submit.prevent="save"><label class="check"><input type="checkbox" v-model="settings.enabled" />Keep automatic-fulfillment prices in sync</label><div class="form-grid"><label>Markup on landed cost · %<input type="number" min="0" max="500" step=".01" v-model.number="settings.markupPercent" required /></label><label class="check"><input type="checkbox" v-model="settings.round99" />Round product prices up to .99</label></div>
<p class="help-copy">Landed cost includes goods, shipping and available supplier taxes/fees. We apply the markup and payment-fee reserve, then show shipping separately without adding it twice. Listing prices are estimates; the delivery quote is the final price before payment. Fixed-price products keep your override and still use loss protection.</p>
<details><summary>Cost allowances</summary><div class="form-grid"><label>Payment fee reserve · %<input type="number" min="0" max="25" step=".01" v-model.number="settings.feePercent" required /></label><label>Payment fee reserve per unit · USD<input type="number" min="0" max="100" step=".01" v-model.number="settings.feeFixed" required /></label><label>Tax/fee allowance when the supplier cannot quote it · %<input type="number" min="0" max="50" step=".01" v-model.number="settings.unknownTaxPercent" required /></label></div><p class="help-copy">These are estimates, not settled fees. Mouser returns tax and fees in its preview. Printify needs an allowance until the order reports tax. Listing estimates refresh roughly every 30 minutes; checkout rechecks current costs. New prices may take a few minutes to populate after saving.</p></details>
<div class="admin-actions"><button class="button primary" :disabled="busy">{{busy?'Saving…':'Save pricing rules'}}</button><button class="button small" type="button" :disabled="busy" @click="load">Refresh price status</button></div></form>
<div v-if="prices.length" class="supplier-table"><table class="admin-table"><thead><tr><th>Product / variant</th><th>Landed cost estimate</th><th>Current listing estimate</th><th>Availability / checked</th></tr></thead><tbody><tr v-for="row in prices" :key="row.id+':'+row.variantId"><td>{{name(row.id)}}<small v-if="row.variantId"> · {{row.variantId}}</small></td><td>{{money(row.landedCents)}}<small v-if="row.shippingCents!=null"> · includes {{money(row.shippingCents)}} shipping</small></td><td>{{money(row.priceCents)}} + quoted shipping</td><td>{{row.available?'Available':'Unavailable'}} · {{new Date(row.checkedAt*1000).toLocaleString()}}<p v-if="row.error" class="notice">{{row.error}}</p></td></tr></tbody></table></div>
<p class="help-copy">Printify and automatic Mouser products use these rules now. AliExpress and Yuzu will use this same policy when their automatic integrations are connected. Pricing holds and paid orders requiring review remain in Orders.</p>
</section>
</template>
<style scoped>
.admin-section { min-width: 0; }
.supplier-table { width: 100%; overflow-x: auto; margin-top: 1rem; }
.admin-table { width: 100%; border-collapse: collapse; text-align: left; }
th, td { padding: .75rem; border-bottom: 1px solid var(--border, #444); vertical-align: top; }
@media (max-width: 700px) { .admin-actions { flex-wrap: wrap; } .form-grid { grid-template-columns: minmax(0, 1fr); } }
</style>
