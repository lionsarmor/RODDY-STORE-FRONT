<script setup>
import { computed, ref } from 'vue';
import { priceLabel, variantLabel, shippingFor, money, sortSizes, compareSizes } from '../merch.js';
const props = defineProps({product: Object, liveProduct: Object});
const search = ref('');
const sizeFilter = ref('');
const bulkPrice = ref('');
const sizes = computed(() => sortSizes([...new Set(props.product.merch.variants.map(v => v.size))]));
const filtered = computed(() => props.product.merch.variants.filter(v => (!sizeFilter.value || v.size === sizeFilter.value) && `${v.color} ${v.size} ${v.sku}`.toLowerCase().includes(search.value.toLowerCase())).sort((a,b) => a.color.localeCompare(b.color) || compareSizes(a.size,b.size)));
function applyPrice() {
  const price = Number(bulkPrice.value);
  if (!Number.isFinite(price) || price <= 0) return;
  filtered.value.forEach(v => v.price = money(price));
  updateBase();
}
function updateBase() {
  const prices = props.product.merch.variants.filter(v => v.enabled).map(v => v.price);
  if (prices.length) props.product.price = Math.min(...prices);
}
function live(v) { return props.liveProduct?.variants.find(x => x.id === v.providerVariantId); }
function cost(v) { const cents = live(v)?.costCents; return Number.isFinite(cents) ? cents / 100 : null; }
function margin(v) { return cost(v) === null || !v.price ? '—' : `${Math.round((v.price-cost(v))/v.price*100)}%`; }
function toggleCountry(country) {
  const countries = props.product.merch.shippingCountries;
  if (countries.includes(country)) countries.splice(countries.indexOf(country),1);
  else countries.push(country);
}
const shippingRows = computed(() => {
  const rows = new Map();
  for (const country of props.product.merch.shippingCountries) {
    for (const v of props.product.merch.variants.filter(v => v.enabled)) {
      const r = shippingFor(props.product,v,country);
      const key=JSON.stringify([country,r?.firstItem,r?.additionalItem]);
      const row=rows.get(key) || {country, first:r?.firstItem, additional:r?.additionalItem, sizes:new Set()};
      row.sizes.add(v.size); rows.set(key,row);
    }
  }
  return [...rows.values()];
});
const usd = n => Number.isFinite(n) ? `$${n.toFixed(2)}` : 'Unavailable';
</script>
<template>
  <section class="merch-editor">
    <div class="field-heading"><h3>Colors, sizes & retail prices</h3><strong>{{ priceLabel(product) }} USD</strong></div>
    <p class="help-copy">{{ product.merch.variants.length }} combinations imported from Printify. Last synced {{ new Date(product.merch.syncedAt).toLocaleString() }}. Prices here control the storefront; editing them does not change Printify's listing prices.</p>
    <p class="help-copy">Printify product: <code>{{ product.merch.productId }}</code> · Store {{ product.merch.shopId }}. Stock is a snapshot; refresh from Printify when updating the listing.</p>
    <div class="form-grid">
      <label>Find color or SKU<input v-model="search" type="search" placeholder="Black, Navy…" /></label>
      <label>Filter size<select v-model="sizeFilter"><option value="">All sizes</option><option v-for="size in sizes" :key="size">{{ size }}</option></select></label>
      <label>Set price for filtered rows (USD)<input v-model="bulkPrice" type="number" min="0.01" step="0.01" /></label>
      <div class="admin-actions"><button class="button small" type="button" :disabled="!filtered.length || !Number.isFinite(Number(bulkPrice)) || Number(bulkPrice) <= 0" @click="applyPrice">Apply to {{ filtered.length }} rows</button></div>
    </div>
    <div class="table-scroll">
      <table class="admin-table merch-variant-table"><thead><tr><th>Offer</th><th>Color / Size</th><th>Stock</th><th>Retail USD</th><th v-if="liveProduct">Production cost</th><th v-if="liveProduct">Gross profit / margin</th></tr></thead>
      <tbody><tr v-for="v in filtered" :key="v.id">
        <td><input v-model="v.enabled" type="checkbox" :aria-label="`Offer ${variantLabel(v)}`" @change="updateBase" /></td>
        <td><strong>{{ variantLabel(v) }}</strong><small>{{ v.sku || v.id }}</small></td>
        <td>{{ v.available === true ? 'In stock' : v.available === false ? 'Out of stock' : 'Unconfirmed' }}</td>
        <td><input v-model.number="v.price" type="number" min=".01" step=".01" :aria-label="`Retail price ${variantLabel(v)}`" @change="updateBase" /></td>
        <td v-if="liveProduct">{{ usd(cost(v)) }}</td>
        <td v-if="liveProduct">{{ cost(v) === null ? '—' : usd(money(v.price-cost(v))) }} / {{ margin(v) }}</td>
      </tr></tbody></table>
    </div>
    <p class="help-copy">Gross profit excludes payment fees, taxes, returns and shipping. Production costs are read privately from Printify and are not published in the storefront catalog.</p>
    <h3>Customer shipping</h3>
    <div class="admin-actions"><label v-for="country in ['US','CA']" :key="country" class="check"><input type="checkbox" :checked="product.merch.shippingCountries.includes(country)" @change="toggleCountry(country)" />{{ country === 'US' ? 'United States' : 'Canada' }}</label></div>
    <p v-if="product.merch.shippingWarning" class="notice">{{ product.merch.shippingWarning }}</p>
    <div class="table-scroll"><table class="admin-table"><thead><tr><th>Country</th><th>Sizes</th><th>First item</th><th>Additional item</th></tr></thead><tbody>
      <tr v-for="row in shippingRows" :key="JSON.stringify([row.country,row.first,row.additional])"><td>{{ row.country }}</td><td>{{ sortSizes([...row.sizes]).join(', ') }}</td><td>{{ usd(row.first) }}</td><td>{{ usd(row.additional) }}</td></tr>
    </tbody></table></div>
    <p class="help-copy">USD standard shipping rates imported from Printify for the matching variants. These are estimates; final checkout needs an address-specific quote. Missing rates are shown as unavailable, never free.</p>
    <p class="notice">Merchandise payment and automatic production are not enabled yet. Publish these options to let customers browse and save their selections.</p>
  </section>
</template>
