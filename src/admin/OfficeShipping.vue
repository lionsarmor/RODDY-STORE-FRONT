<script setup>
const props = defineProps({product: Object});
function destination(country, enabled) {
  const countries = new Set(props.product.shippingCountries || ['US','CA']);
  if (enabled) countries.add(country); else countries.delete(country);
  props.product.shippingCountries = [...countries];
}
function toggle(country, enabled) {
  props.product.officeShipping ||= {};
  if (enabled) props.product.officeShipping[country] = {firstItem: 0, additionalItem: 0};
  else delete props.product.officeShipping[country];
}
</script>
<template>
  <section>
    <template v-if="product.supplier?.provider === 'aliexpress' && product.supplier.fulfillment === 'manual'">
      <h3>Shipping destinations</h3>
      <p class="help-copy">Offer only countries verified for this exact listing, seller and variant. Shipping is quoted live before payment; you place the paid order manually from Orders.</p>
      <label v-for="country in ['US','CA']" :key="country" class="check"><input type="checkbox" :checked="(product.shippingCountries || ['US','CA']).includes(country)" @change="destination(country,$event.target.checked)" />{{country === 'US' ? 'United States' : 'Canada'}}</label>
    </template>
    <template v-else>
    <h3>{{ product.supplier?.fulfillment === 'manual' ? 'Shipping charges' : 'Ships from your office' }}</h3>
    <p class="help-copy">Enable each destination only when its rates are ready. Rates are in USD and charged per product: first item plus each additional item. Different office products' shipping charges add together. Leave a country off to prevent orders to that destination.</p>
    <div v-for="country in ['US','CA']" :key="country" class="mb-6">
      <label class="check"><input type="checkbox" :checked="!!product.officeShipping?.[country]" @change="toggle(country, $event.target.checked)" />{{ country === 'US' ? 'United States' : 'Canada' }}</label>
      <div v-if="product.officeShipping?.[country]" class="form-grid">
        <label>First item shipping USD<input v-model.number="product.officeShipping[country].firstItem" type="number" min="0" step=".01" /></label>
        <label>Each additional item USD<input v-model.number="product.officeShipping[country].additionalItem" type="number" min="0" step=".01" /></label>
      </div>
    </div>
    <p v-if="product.supplier?.fulfillment === 'manual'" class="help-copy">These are the shipping amounts charged to your customer. Check the actual shipping cost when placing each paid supplier order, and save its invoice and tracking in Orders. Local inventory is not used.</p>
    <p v-else class="help-copy">Publish shipping changes with the catalog. Use Orders → Office inventory to set actual on-hand stock; the backend reserves it during checkout and deducts it after confirmed payment. Set availability to “Available” only when the product is ready to ship.</p>
    </template>
  </section>
</template>
