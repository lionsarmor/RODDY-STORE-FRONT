<script setup>
import { computed, ref } from 'vue';
import { commerceRequest } from './commerce-api.js';
const props = defineProps({ catalog: Object, token: String });
const kits = computed(() => props.catalog.products.filter(p => p.supplier?.bom));
const quantity = ref(1), country = ref('US'), busy = ref(false), error = ref(''), message = ref(''), carts = ref([]);
const api = (body) => commerceRequest(props.catalog.settings.checkoutEndpoint, '/admin/kit-carts', props.token, body);
async function run(productId) {
  if (busy.value) return;
  busy.value = true; error.value = ''; message.value = '';
  try {
    if (productId) { const result = await api({productId, quantity: quantity.value, country: country.value}); message.value = result.message; }
    carts.value = (await api()).carts;
  } catch (e) { error.value = e.message; }
  finally { busy.value = false; }
}
</script>
<template>
  <section class="admin-section">
    <h3>Kit carts</h3>
    <p class="help-copy">Reuse each published revision’s parts list. Every click creates a fresh, private API cart; it does not place an order or charge a card. Customer checkout always builds its own cart and checks live quantities, prices and shipping.</p>
    <label>Number of kits<input v-model.number="quantity" type="number" min="1" max="99" /></label><label>Destination country<select v-model="country"><option value="US">United States</option><option value="CA">Canada</option></select></label>
    <p v-if="!kits.length">Create a Mouser BOM in a product’s Parts kit tab first.</p>
    <ul><li v-for="p in kits" :key="p.id"><strong>{{p.name}}</strong> · {{p.supplier.bom.revision || 'No revision'}} · {{p.supplier.bom.lines.length}} part lines · {{p.supplier.bom.status}} <button class="button small" :disabled="busy || p.supplier.bom.status!=='ready'" @click="run(p.id)">Build fresh cart</button></li></ul>
    <button class="button small" :disabled="busy" @click="run()">Load saved cart references</button>
    <p v-if="message" class="notice" role="status">{{message}}</p><p v-if="error" class="notice" role="alert">{{error}}</p>
    <ul><li v-for="cart in carts" :key="cart.cart">{{cart.product}} · {{cart.revision}} · {{cart.quantity}} kit(s) · {{cart.country}} · {{new Date(cart.created*1000).toLocaleString()}}<br /><code>{{cart.cart}}</code></li></ul>
    <p class="help-copy">These are API references, not website Share Access IDs. To save a cart in My Mouser, download the product’s BOM CSV, import it on Mouser, and save it as a project. Saved references are historical; availability is not reserved.</p>
  </section>
</template>
<style scoped>
li { margin: 1rem 0; overflow-wrap: anywhere; }
code { font-size: .8rem; }
</style>
