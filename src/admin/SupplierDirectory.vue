<script setup>
import { ref, watch } from 'vue';
import { dispatchRequest } from './supplier-dispatch.js';
import { commerceRequest } from './commerce-api';
const props = defineProps({ endpoint: String, token: String, connected: Boolean });
const emit = defineEmits(['navigate', 'connection']);
const suppliers = ref([]), busy = ref(false), error = ref(''), message = ref(''), selected = ref('mouser');
const api = body => commerceRequest(props.endpoint, '/admin/suppliers/directory', props.token, body);
async function run(fn) {
  if (busy.value) return;
  busy.value = true; error.value = ''; message.value = '';
  try { await fn(); } catch(e) { error.value = e.message; } finally { busy.value = false; }
}
async function load() { suppliers.value = (await api()).suppliers; }
watch(() => [props.connected, props.token], () => { suppliers.value = []; if(props.connected) run(load); }, {immediate: true});
async function save(supplier) {
  const result = await api({provider: supplier.provider, revision: supplier.revision, settings: supplier.settings});
  // Preserve unsaved edits to other supplier cards.
  suppliers.value = suppliers.value.map(s => s.provider === supplier.provider ? result.suppliers.find(r => r.provider === s.provider) : s);
  message.value = `${supplier.name} settings saved privately. Apply the instructions when placing each order.`;
}
async function copy(s) { await navigator.clipboard.writeText(dispatchRequest(s)); message.value = 'Dispatch request copied. Send it to the supplier and obtain confirmation.'; }
</script>
<template>
  <section class="admin-section supplier-directory">
    <p class="eyebrow">YOUR SUPPLIER DESK</p><h2>Build it. Order it. Ship it.</h2>
    <p>Keep contacts, services and packing agreements together. These settings stay on the droplet. They do not change product availability, send messages or place orders.</p>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p><p v-if="message" class="notice" role="status">{{ message }}</p>
    <div class="directory-tabs" role="group" aria-label="Supplier settings">
      <button v-for="s in suppliers" :key="s.provider" type="button" :aria-pressed="selected === s.provider" @click="selected = s.provider"><strong>{{ s.name }}</strong><small>{{ s.workflow }}</small></button>
    </div>
    <fieldset v-for="s in suppliers.filter(s => s.provider === selected)" :key="s.provider" :disabled="busy">
      <h3>{{ s.name }}</h3><p class="notice">{{ s.api }}</p>
      <div class="admin-actions">
        <a :href="s.website" target="_blank" rel="noopener noreferrer" class="button small">Open supplier ↗</a>
        <button v-if="['mouser','aliexpress'].includes(s.provider)" class="button small" @click="emit('connection', s.provider)">Manage API connection</button>
        <button v-if="s.provider === 'pcbway'" class="button small" @click="emit('navigate','pcb')">Open PCB project wizard</button>
        <button v-if="s.provider === 'printify'" class="button small" @click="emit('navigate','printify')">Manage Printify</button>
        <button class="button small" @click="emit('navigate','orders')">Open Orders</button>
      </div>
      <div class="form-grid">
        <label>Contact / account manager<input v-model="s.settings.contact" maxlength="250" placeholder="Name and business email" /></label>
        <label>Your account reference<input v-model="s.settings.accountReference" maxlength="160" placeholder="Reference only — no passwords or API keys" /></label>
        <label>Minimum order / batch size<input v-model="s.settings.minimumOrder" maxlength="160" placeholder="Awaiting confirmation" /></label>
        <label>Production + dispatch time<input v-model="s.settings.leadTime" maxlength="160" placeholder="Awaiting confirmation" /></label>
      </div>
      <h4>Services to arrange</h4><div class="admin-actions"><label v-for="service in s.services" :key="service" class="check"><input v-model="s.settings.services" :value="service" type="checkbox" />{{ service }}</label></div>
      <p class="help-copy">Planning notes; selecting a service does not establish supplier approval.</p>
      <div class="form-grid">
        <label>Preferred dispatch<select v-model="s.settings.dispatch"><option value="confirm-per-order">Confirm for each order</option><option value="customer">Direct to customer, where agreed</option><option value="self">To me for inspection / repacking</option></select></label>
        <label>Requested packaging<select v-model="s.settings.packaging"><option value="neutral">Neutral / unbranded</option><option value="roddy">RODDY branded, where agreed</option><option value="standard">Standard supplier packaging</option></select></label>
      </div>
      <h4>Destinations discussed with supplier</h4><div class="admin-actions"><label v-for="(name,code) in {US:'United States',CA:'Canada'}" :key="code" class="check"><input v-model="s.settings.countries" :value="code" type="checkbox" />{{ name }}</label></div>
      <p class="help-copy">Control customer checkout separately in each product’s Options & shipping tab.</p>
      <h4>Paperwork & packing agreement</h4>
      <label class="check"><input v-model="s.settings.omitPriceReceipts" type="checkbox" />Request no supplier retail price receipts in the parcel</label>
      <label class="check"><input v-model="s.settings.omitPromotions" type="checkbox" />Request no supplier advertising or promotional inserts</label>
      <div class="form-grid">
        <label>Agreement status<select v-model="s.settings.agreementStatus"><option value="unconfirmed">Not confirmed</option><option value="requested">Requested — awaiting reply</option><option value="confirmed">Confirmed by supplier</option><option value="unavailable">Supplier cannot offer this</option></select></label>
        <label>Confirmation record<textarea v-model="s.settings.agreementEvidence" maxlength="1000" placeholder="Who agreed, date, exact seller/warehouse, and any exceptions" /></label>
      </div>
      <label>Instructions to copy into supplier orders<textarea v-model="s.settings.instructions" rows="5" maxlength="2500" /></label>
      <p class="help-copy">A saved request is not a supplier guarantee. Keep required customs, safety, warranty and identification documents. If neutral shipping cannot be confirmed, arrange delivery to yourself for inspection and repacking.</p>
      <div class="admin-actions"><button class="button primary" @click="run(() => save(s))">Save {{ s.name }} settings</button><button class="button small" @click="run(() => copy(s))">Copy dispatch request</button><button class="button small" @click="run(load)">Reload saved settings</button></div>
    </fieldset>
  </section>
</template>
<style scoped>
.directory-tabs{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:24px 0}.directory-tabs button{text-align:left;padding:16px;border:1px solid #5b6770;border-radius:12px;background:#172027;color:#f5f3e9}.directory-tabs button[aria-pressed=true]{background:#bfe5f3;color:#172027;border-color:#bfe5f3}.directory-tabs strong{display:block;font-size:16px}.directory-tabs small{display:block;line-height:1.5;margin-top:8px}.supplier-directory h4{margin:24px 0 12px}.supplier-directory fieldset{min-width:0}.supplier-directory textarea{width:100%}
</style>
