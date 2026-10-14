<script setup>
import { SHIPPING_COUNTRIES, shippingCountries, setShippingCountry, shippingLabel } from '../shipping-destinations.js';
defineProps({ product: Object });
</script>
<template>
  <section class="destination-settings">
    <h3>Where can this product ship?</h3>
    <p class="help-copy">Choose the countries customers can order from. Publish to update the listing and checkout. Rates and supplier coverage must also support the destination.</p>
    <div class="admin-actions">
      <label v-for="(name, code) in SHIPPING_COUNTRIES" :key="code" class="check">
        <input type="checkbox" role="switch" :aria-label="`Ship to ${name}`" :checked="shippingCountries(product).includes(code)" @change="setShippingCountry(product, code, $event.target.checked)" />{{ name }}
      </label>
    </div>
    <p class="notice">Listing: {{ shippingLabel(product) }}</p>
  </section>
</template>
