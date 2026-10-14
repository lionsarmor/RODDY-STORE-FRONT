<script setup>
import { shippingCountries, SHIPPING_COUNTRIES } from '../shipping-destinations.js';
const props = defineProps({product: Object});
function addRate(country) {
  props.product.officeShipping ||= {};
  props.product.officeShipping[country] ||= {firstItem: 0, additionalItem: 0};
}
</script>
<template>
  <section>
    <template v-if="product.supplier?.provider === 'aliexpress' && product.supplier.fulfillment === 'manual'">
      <h3>Live shipping quotes</h3>
      <p class="help-copy">Shipping is quoted for the selected country, exact listing, seller and variant before payment. Place paid orders manually from Orders.</p>
    </template>
    <template v-else>
      <h3>Customer shipping charges</h3>
      <p class="help-copy">USD per product: first item plus each additional item. Zero means free shipping. Turning a destination off keeps its saved rates for later.</p>
      <div v-for="country in shippingCountries(product)" :key="country" class="mb-6">
        <h4>{{ SHIPPING_COUNTRIES[country] }}</h4>
        <div v-if="product.officeShipping?.[country]" class="form-grid">
          <label>First item shipping USD<input v-model.number="product.officeShipping[country].firstItem" type="number" min="0" step=".01" /></label>
          <label>Each additional item USD<input v-model.number="product.officeShipping[country].additionalItem" type="number" min="0" step=".01" /></label>
        </div>
        <p v-else class="notice">Add a shipping rate before offering this destination. <button type="button" class="button small" @click="addRate(country)">Set {{ country }} rate</button></p>
      </div>
      <p v-if="product.supplier?.fulfillment === 'manual' || product.keycaps" class="help-copy">These amounts are charged to your customer. Check the actual supplier cost when placing a paid order, then save its invoice and tracking in Orders.</p>
      <p v-else class="help-copy">Publish shipping changes with the catalog. Manage on-hand stock in Orders → Office inventory.</p>
    </template>
  </section>
</template>
