<script setup>
import { ref } from 'vue';
import { commerceRequest } from './commerce-api';
import { dispatchRequest } from './supplier-dispatch.js';
const props = defineProps({ endpoint: String, token: String, kind: String, reference: String });
const supplier = ref(null), error = ref(''), busy = ref(false), copied = ref(false);
async function load(event) {
  if (!event.target.open || busy.value) return;
  busy.value = true; error.value = ''; copied.value = false;
  try {
    const data = await commerceRequest(props.endpoint, '/admin/suppliers/directory', props.token);
    supplier.value = data.suppliers.find(s => s.provider === (props.kind === 'keycaps' ? 'yuzu' : props.kind));
  } catch(e) { error.value = e.message; } finally { busy.value = false; }
}
async function copy() {
  try { await navigator.clipboard.writeText(dispatchRequest(supplier.value, props.reference)); copied.value = true; }
  catch { error.value = 'Select and copy the request below.'; }
}
</script>
<template>
  <details class="dispatch-note" @toggle="load">
    <summary>Packing instructions & supplier agreement</summary>
    <p v-if="error" role="alert">{{ error }}</p><p v-if="busy">Loading saved instructions…</p>
    <template v-if="supplier">
      <p>Current saved request · {{ supplier.settings.agreementStatus }}. Confirm it applies to this seller and shipment.</p>
      <pre>{{ dispatchRequest(supplier, reference) }}</pre>
      <button type="button" class="button small" @click="copy">{{ copied ? 'Copied ✓' : 'Copy packing request' }}</button>
      <p>Copy this into the supplier order. Nothing is sent automatically. Manage agreements in Suppliers & imports.</p>
    </template>
  </details>
</template>
<style scoped>
.dispatch-note{margin:16px 0;font-size:12px}.dispatch-note summary{cursor:pointer;font-weight:700}.dispatch-note pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.6 monospace;background:#0002;padding:12px;margin:12px 0}.dispatch-note p{margin:12px 0;line-height:1.5}
</style>
