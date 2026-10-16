<script setup>
import { computed, ref } from 'vue';
const props = defineProps({ product: Object });
const error = ref('');
const bom = computed(() => props.product.supplier?.bom);
function start() {
  props.product.supplier = { provider: 'mouser', supplierSku: `kit-${props.product.id}`, fulfillment: 'automatic', minimumQuantity: 1, orderMultiple: 1,
    bom: { revision: '', status: 'draft', lines: [] } };
  props.product.trackStock = false;
}
async function upload(event) {
  error.value = '';
  try {
    const file = event.target.files[0];
    if (!file || file.size > 300000) throw new Error('Choose a BOM JSON file smaller than 300 KB.');
    const data = JSON.parse(await file.text());
    if (!Array.isArray(data.lines) || data.lines.length > 250) throw new Error('BOM JSON needs a lines array (maximum 250).');
    if (data.lines.some(l => !l || typeof l.supplierSku !== 'string' || !Number.isInteger(l.quantity) || l.quantity < 1)) throw new Error('Each BOM line needs a Mouser part number and a positive whole quantity.');
    if (!bom.value) start();
    props.product.supplier.bom = { ...data, status: 'draft' };
  } catch (e) { error.value = e.message; }
  event.target.value = '';
}
function download() {
  const rows = [['Mouser Part Number', 'Quantity'], ...bom.value.lines.map(l => [l.supplierSku, l.quantity])];
  const csv = rows.map(row => row.map(v => '"' + String(v ?? '').replaceAll('"', '""') + '"').join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], {type:'text/csv'}));
  const a = document.createElement('a'); a.href = url; a.download = `${props.product.id}-${bom.value.revision || 'draft'}-mouser.csv`; a.click(); URL.revokeObjectURL(url);
}
</script>
<template>
  <section class="admin-section">
    <h3>Mouser parts-kit BOM</h3>
    <p class="help-copy">One template per hardware revision. Quantities are Mouser order units per kit: a bag of ten switches is one order unit. Include all sockets, connectors and harness parts; bare PCBs are a separate RODDY product.</p>
    <button v-if="!product.supplier" class="button small" @click="start">Create a parts-kit template</button>
    <template v-if="bom">
      <label>Hardware / BOM revision<input v-model="bom.revision" placeholder="C8-P6-v1" maxlength="80" /></label>
      <label>Procurement readiness<select v-model="bom.status"><option value="draft">Draft — missing or unverified parts; purchasing blocked</option><option value="ready">Complete exact BOM — allow live supplier quotes</option></select></label>
      <p class="help-copy">“Complete” means every ordered part and quantity is identified for this board revision. Physical testing may still be incomplete; keep the red prototype warning on the listing. Publishing a changed BOM creates a new supplier mapping; paid orders keep their original parts.</p>
      <div class="table-scroll"><table><thead><tr><th>Mouser part number</th><th>Order units / kit</th><th>Notes / pack contents</th><th></th></tr></thead><tbody>
        <tr v-for="(line,index) in bom.lines" :key="index"><td><input v-model="line.supplierSku" aria-label="Mouser part number" /></td><td><input v-model.number="line.quantity" type="number" min="1" max="10000" aria-label="Order units per kit" /></td><td><input v-model="line.note" aria-label="Part and pack notes" /></td><td><button class="text-button" @click="bom.lines.splice(index,1)">Remove</button></td></tr>
      </tbody></table></div>
      <div class="admin-actions"><button class="button small" @click="bom.lines.push({supplierSku:'',quantity:1,note:''})">Add part</button><button class="button small" @click="download">Download Mouser import CSV</button></div>
    </template>
    <label v-if="!product.supplier || bom">Import revision BOM JSON<input type="file" accept=".json,application/json" @change="upload" /></label>
    <p v-if="error" class="notice" role="alert">{{ error }}</p>
    <p v-if="bom" class="help-copy">Publish your catalog changes, then use Suppliers → Kit carts to build a fresh cart. For a website saved project, import the CSV in My Mouser and save it there. API cart references are not website sharing links.</p>
  </section>
</template>
<style scoped>
.table-scroll { max-width: 100%; overflow-x: auto; }
table { width: 100%; min-width: 560px; }
input[type=number] { max-width: 8rem; }
</style>
