<script setup>
import {ref, reactive, computed, onMounted, watch} from 'vue';
import {commerceRequest} from './commerce-api';
const props = defineProps({endpoint: String, token: String, connected: Boolean, refreshKey: Number});
const orders = ref([]), inventory = ref([]), busy = ref(false), error = ref(''), message = ref(''), filter = ref('all');
const drafts = reactive({});
const shown = computed(() => orders.value.filter(o => filter.value === 'all' || (filter.value === 'attention' ? (o.orderPacket?.error || o.fulfillments.some(f => f.error || f.state === 'review')) : filter.value === 'keycaps' ? o.payment_status === 'paid' && o.fulfillments.some(f=>f.kind==='keycaps' && f.state==='awaiting-submission') : filter.value === 'office' ? o.payment_status === 'paid' && o.fulfillments.some(f => f.kind === 'office' && f.state === 'ready-to-ship') : o.payment_status === filter.value)));
const money = n => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);
const request = (path, body) => commerceRequest(props.endpoint, path, props.token, body);
async function refresh() {
  const data = await request('/admin/orders'+(filter.value==='keycaps'?'?view=keycaps':'')); orders.value = data.data;
  const stock = await request('/admin/inventory'); inventory.value = stock.items;
  for (const i of inventory.value) drafts['stock:'+i.id] = i.stock;
}
async function run(action) {
  busy.value = true; error.value = ''; message.value = '';
  try { await action(); } catch(e) { error.value = e.message; }
  finally { busy.value = false; }
}
function load() { return run(refresh); }
function stock(item) { return run(async () => { await request('/admin/inventory/'+encodeURIComponent(item.id), {stock: Number(drafts['stock:'+item.id])}); await refresh(); message.value='Live office stock saved.'; }); }
function shipment(order,kind='office') { return run(async () => { await request('/admin/orders/'+order.id+'/shipment', {...drafts[order.id+':'+kind],kind}); await refresh(); message.value='Tracking saved to the customer order page.'; }); }
async function downloadPackets(path,filename,body={}) {
  const response=await fetch(props.endpoint.replace(/\/$/,'')+path,{method:'POST',headers:{'content-type':'application/json',authorization:'Bearer '+props.token},body:JSON.stringify(body)});
  if(!response.ok)throw new Error((await response.json()).error || 'Could not download this packet.');
  const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function packet(order){return run(()=>downloadPackets('/admin/orders/'+order.id+'/keycaps','RODDY-'+order.id+'-keycaps.zip',{action:'download'}));}
function pendingPackets(){return run(()=>downloadPackets('/admin/keycaps/packets','RODDY-pending-keycap-orders.zip'));}
function submitted(order,checked=true){return run(async()=>{await request('/admin/orders/'+order.id+'/keycaps',{action:checked?'submitted':'pending',supplierReference:drafts['supplier:'+order.id] || ''});await refresh();message.value=checked?'Checked off as submitted. Add tracking when it ships.':'Returned to the new keycap orders queue.';});}
function reconcile(order) { return run(async () => { await request('/admin/orders/'+order.id+'/reconcile', {}); await refresh(); message.value='Existing supplier order linked. The worker will refresh production and tracking.'; }); }
function cancel(order) { return run(async () => { await request('/admin/orders/'+order.id+'/cancel', {}); await refresh(); message.value='Unpaid checkout canceled and office reservations released.'; }); }
function shippingDraft(order,kind='office') { return drafts[order.id+':'+kind] ||= {carrier:'',number:'',url:''}; }
watch(()=>props.refreshKey,()=>{if(props.connected)load();});
watch(filter,()=>{if(props.connected)load();});
watch(() => props.connected, connected => { if (!connected) { orders.value = []; inventory.value = []; } });
onMounted(() => {if(props.connected) load();});
</script>
<template>
  <section class="order-manager">
    <div class="section-heading"><p class="help-copy">One order can contain downloads, Printify products and office shipments. Payments and production refresh automatically; use Square for receipts and refunds. Tracking is available on the customer's private order page. Latest 100 checkout attempts are shown; the New keycap orders view shows the oldest 100 awaiting submission.</p><div class="admin-actions"><button class="button small" :disabled="!connected || busy" @click="load">{{busy ? 'Loading…' : 'Refresh orders & stock'}}</button><a href="https://squareup.com/dashboard/sales/transactions" target="_blank" rel="noopener noreferrer" class="button small">Open Square ↗</a><a href="https://printify.com/app/orders" target="_blank" rel="noopener noreferrer" class="button small">Open Printify ↗</a></div></div>
    <p v-if="error" class="notice" role="alert">{{error}}</p><p v-if="message" class="notice" role="status">{{message}}</p>
    <div class="admin-actions"><button class="button primary small" :disabled="busy || !connected" @click="filter='keycaps'">New keycap orders</button><button class="button small" :disabled="busy || !connected" @click="pendingPackets">Download pending keycap packets ↓</button></div>
    <p class="help-copy">Paid custom keycap designs are saved on your droplet. Download them straight to this computer; no email service is needed. Import only the *-yuzu.json files into the maker editor. ORDER_DETAILS.json is your private fulfillment record. Check off a set after placing the maker order manually. Batch downloads include up to 100 pending sets of orders.</p>
    <h3>Office inventory</h3><p class="help-copy">Live on-hand counts include unpaid reservations. Paid orders deduct stock once. Catalog stock seeds a new product only; restock here so publishing an old catalog cannot restore sold inventory.</p>
    <div class="product-table-wrap"><table class="admin-table"><thead><tr><th>Product</th><th>Available</th><th>Reserved</th><th>On hand</th><th></th></tr></thead><tbody><tr v-for="item in inventory" :key="item.id"><td>{{item.name}}</td><td>{{item.available}}</td><td>{{item.reserved}}</td><td><input v-model="drafts['stock:'+item.id]" type="number" min="0" step="1" :aria-label="`On-hand stock for ${item.name}`" /></td><td><button class="button small" :disabled="busy" @click="stock(item)">Save live stock</button></td></tr></tbody></table></div>
    <label class="order-filter">Show orders<select v-model="filter"><option value="all">All attempts</option><option value="paid">Paid</option><option value="keycaps">New keycap orders: submit to maker</option><option value="office">Office: ready to ship</option><option value="attention">Needs attention</option><option value="unconfirmed">Unconfirmed</option><option value="canceled">Canceled</option></select></label>
    <article v-for="order in shown" :key="order.id" class="order-card">
      <div class="field-heading"><h3>{{order.id.slice(-12).toUpperCase()}}</h3><strong>{{money(order.amount_total)}} · {{order.payment_status}}</strong></div>
      <p class="help-copy">{{new Date(order.created*1000).toLocaleString()}} · Square {{order.providerId || 'not created'}}</p>
      <button v-if="order.payment_status === 'unconfirmed'" class="button small" :disabled="busy" @click="cancel(order)">Cancel unpaid checkout</button>
      <ul><li v-for="item in order.items" :key="item.id+item.label">{{item.qty}} × {{item.name}} {{item.label}} · {{item.kind === 'printify' ? 'made to order' : item.kind === 'office' ? 'office shipment' : item.kind === 'keycaps' ? 'custom keycaps' : 'digital download'}}</li></ul>
      <address v-if="order.address">{{order.address.first_name}} {{order.address.last_name}}<br />{{order.address.address1}} {{order.address.address2}}<br />{{order.address.city}}, {{order.address.region}} {{order.address.zip}} · {{order.address.country}}<br />{{order.address.email}} · {{order.address.phone}}</address>
      <div v-if="order.payment_status === 'paid' && order.items.some(i=>i.kind==='keycaps')" class="order-fulfillment"><button class="button small" :disabled="busy" @click="packet(order)">Download keycap JSON & order packet ↓</button><p class="help-copy">Droplet packet: {{order.orderPacket?.state || 'queued'}}. Downloading does not submit the order to the maker.</p><p v-if="order.orderPacket?.error" class="notice">{{order.orderPacket.error}}</p></div>
      <section v-for="f in order.fulfillments" :key="f.kind" class="order-fulfillment"><strong>{{f.kind === 'office' ? 'Office shipment' : f.kind === 'keycaps' ? 'Custom keycaps' : 'Printify'}}: {{f.state}}</strong><p v-if="f.supplierId" class="help-copy">Supplier order {{f.supplierId}}</p><p v-if="f.error" class="notice">{{f.error}}</p><p v-for="s in f.shipments" :key="s.number">{{s.carrier}} · {{s.number}} <a v-if="s.url" :href="s.url" target="_blank" rel="noopener noreferrer">Track ↗</a></p><button v-if="f.kind === 'printify' && f.state === 'review'" class="button small" :disabled="busy" @click="reconcile(order)">Find existing Printify order</button>
        <div v-if="f.kind === 'keycaps' && order.payment_status === 'paid'" class="form-grid"><label>Maker reference (optional)<input v-model="drafts['supplier:'+order.id]" maxlength="150" :placeholder="f.supplierId || 'Yuzu order reference'" /></label><label class="check"><input type="checkbox" :checked="['submitted','shipped'].includes(f.state)" :disabled="busy || f.state==='shipped'" @change="submitted(order,$event.target.checked)" />Submitted to maker ✓</label></div>
        <form v-if="['office','keycaps'].includes(f.kind) && order.payment_status === 'paid'" class="form-grid" @submit.prevent="shipment(order,f.kind)"><label>Carrier<input v-model="shippingDraft(order,f.kind).carrier" placeholder="USPS / UPS…" required /></label><label>Tracking number<input v-model="shippingDraft(order,f.kind).number" required /></label><label class="full">Tracking URL (optional)<input v-model="shippingDraft(order,f.kind).url" type="url" /></label><button class="button small" :disabled="busy">{{f.state === 'shipped' ? 'Update tracking' : 'Mark shipped & save tracking'}}</button></form>
      </section>
    </article>
    <p v-if="!shown.length" class="empty-state">No matching orders. Connect and refresh to load the current queue.</p>
  </section>
</template>
<style scoped>
.order-card { border:1px solid var(--color-border,#444); padding:20px; margin:20px 0; overflow-wrap:anywhere; }
.order-card address { font-style:normal; line-height:1.7; margin:16px 0; }
.order-card ul {padding:12px 0; list-style:none; line-height:1.8;}
.order-fulfillment {border-top:1px solid var(--color-border,#444); padding:16px 0;}
.order-filter {display:grid; gap:8px; max-width:300px; margin:24px 0;}
</style>
