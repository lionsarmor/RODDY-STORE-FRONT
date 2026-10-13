<script setup>
import { computed, reactive, ref, watch } from 'vue';
import { commerceRequest } from './commerce-api';
import { priceEstimate, supplierDraft, supplierIdentity } from './supplier-model';
const props = defineProps({catalog: Object, token: String, connected: Boolean});
const emit = defineEmits(['import-products', 'edit-product']);
const state = ref(null);
const preferences = ref({favorites: [], revision: 1});
const credentials = reactive({searchKey: '', appKey: '', appSecret: '', accessToken: ''});
const provider = ref('mouser');
const query = ref('MiSTer FPGA');
const country = ref('US');
const page = ref(1);
const results = ref(null);
const selected = ref([]);
const variants = reactive({});
const favoriteId = ref('');
const category = ref(props.catalog.categories[0]?.id || '');
const review = ref(false);
const busy = ref(false);
const error = ref('');
const message = ref('');
const rules = reactive({mode: 'markup', percent: 30, minimumProfit: 5, shippingBuffer: 15, feePercent: 2.9, feeFixed: .30, round99: true});
const favorite = computed(() => preferences.value.favorites.find(f => f.id === favoriteId.value));
const connection = computed(() => state.value?.connections.find(c => c.provider === provider.value));
const websiteSearch = computed(() => provider.value === 'mouser' ? `https://www.mouser.com/c/?q=${encodeURIComponent(query.value)}` : `https://www.aliexpress.com/w/wholesale-${encodeURIComponent(query.value.replaceAll(' ', '-'))}.html`);
const rows = computed(() => results.value?.products || []);
const selection = computed(() => rows.value.filter(row => selected.value.includes(row.sku)));
const api = (path, body) => commerceRequest(props.catalog.settings.checkoutEndpoint, '/admin/suppliers' + path, props.token, body);
async function act(fn) {
  if (busy.value) return;
  busy.value = true; error.value = ''; message.value = '';
  try { await fn(); } catch (e) { error.value = e.message; }
  finally { busy.value = false; }
}
async function load() { state.value = await api(''); preferences.value = JSON.parse(JSON.stringify(state.value.preferences)); }
watch(() => [props.connected, props.token], async () => {
  state.value = null; results.value = null; selected.value = [];
  Object.keys(credentials).forEach(key => credentials[key] = '');
  if (props.connected) await act(load);
}, {immediate: true});
watch(provider, () => { if (favorite.value && favorite.value.provider !== provider.value) favoriteId.value = ''; results.value = null; selected.value = []; review.value = false; Object.keys(credentials).forEach(key => credentials[key] = ''); });
function setStoreId(f) { if (/^\d{1,20}$/.test(f.storeId || '')) f.url = `https://www.aliexpress.com/store/${f.storeId}`; }
function extractStoreId(f) { try { const match = new URL(f.url).pathname.match(/\/store\/(\d+)/); f.storeId = match?.[1] || ''; } catch { f.storeId = ''; } }
function addFavorite() { preferences.value.favorites.push({id: crypto.randomUUID(), name: '', provider: 'aliexpress', storeId: '', url: '', query: 'MiSTer FPGA'}); }
function chooseFavorite() {
  if (!favorite.value) return;
  provider.value = favorite.value.provider;
  query.value = favorite.value.query || '';
  results.value = null; selected.value = [];
}
async function saveConnection() {
  try { await api('/connections', {provider: provider.value, ...credentials}); await load(); message.value = 'Credentials saved privately. Run a search to verify access. No supplier orders or payments are enabled.'; }
  finally { Object.keys(credentials).forEach(key => credentials[key] = ''); }
}
async function search(next = 1) {
  results.value = await api('/search', {provider: provider.value, query: query.value, country: country.value, page: next});
  page.value = next; selected.value = []; review.value = false;
  state.value = await api('');
  results.value.products = results.value.products.map(row => ({...row, checkedAt: results.value.checkedAt}));
}
async function lookup(value, existingRow) {
  const data = await api('/product', {provider: provider.value, query: value, country: country.value});
  const row = {...data.product, checkedAt: data.checkedAt};
  if (!results.value) results.value = {products: [], hasMore: false, checkedAt: data.checkedAt};
  const i = rows.value.findIndex(r => r.sku === (existingRow?.sku || row.sku));
  if (i < 0) results.value.products.unshift(row); else results.value.products.splice(i, 1, row);
  message.value = `${row.name}: supplier details loaded. Review stock, minimum quantity and variant before importing.`;
}
function chosen(row) { return row.variants?.find(v => v.id === variants[row.sku]); }
function existing(row) { return props.catalog.products.find(p => p.supplier && supplierIdentity(p) === supplierIdentity({...row, variantId: variants[row.sku] || ''})); }
function sellerMatches(row) { return !favorite.value || favorite.value.provider !== 'aliexpress' || (!!favorite.value.storeId && row.sellerId === favorite.value.storeId); }
function eligible(row) { return !!row.sku && !existing(row) && sellerMatches(row) && (row.provider !== 'aliexpress' || !!chosen(row)); }
function estimate(row) { try { return priceEstimate(chosen(row)?.costCents ?? row.costCents, rules); } catch { return null; } }
function dollars(cents) { return Number.isInteger(cents) ? `$${(cents / 100).toFixed(2)}` : 'Unknown'; }
function importSelected() {
  const drafts = [], failures = [];
  if (!props.catalog.categories.some(c => c.id === category.value)) throw new Error('Choose a storefront department.');
  for (const row of selection.value) {
    try {
      if (!eligible(row)) throw new Error(`${row.name}: check the selected variant, preferred seller or existing import.`);
      drafts.push(supplierDraft(row, variants[row.sku], category.value, rules, [...props.catalog.products, ...drafts]));
    } catch (e) { failures.push(e.message); }
  }
  if (drafts.length) emit('import-products', drafts);
  message.value = `${drafts.length} hidden draft(s) added to your catalog draft. Review them in Products, then Publish when ready. Supplier checkout remains unavailable until fulfillment is configured.`;
  error.value = failures.join('\n'); selected.value = []; review.value = false;
}
</script>
<template>
  <div class="supplier-manager">
    <section class="admin-section">
      <p class="eyebrow">DISCOVER · CHOOSE · REVIEW · PUBLISH</p>
      <h2>Suppliers & product imports</h2>
      <p>Search Mouser or AliExpress, select exactly the listings you want, and add hidden drafts to the existing product editor. Searching never adds products automatically.</p>
      <p v-if="!connected" class="notice">Connect to GitHub above to manage supplier connections and private search results.</p>
      <button class="button small" :disabled="!connected || busy" @click="act(load)">Reload supplier settings</button>
      <p v-if="error" class="form-error" role="alert" style="white-space:pre-wrap">{{ error }}</p><p v-if="message" class="notice" role="status">{{ message }}</p>
    </section>
    <fieldset v-if="connected && state" :disabled="busy">
      <section class="admin-section">
        <h2>How payments and fulfillment work</h2>
        <p><strong>Customer → RODDY through Square → your payout bank.</strong> The supplier charges your separate supplier account for goods and shipping. Square does not split a checkout payment or transfer it to Mouser, Printify or AliExpress automatically.</p>
        <p>Printify merchandise already uses the store's paid-order fulfillment flow. Mouser and AliExpress search/import connections below do not enable purchasing. Their API ordering, account billing, exact SKU, landed cost, shipping quote and tracking still need verification before direct supplier sales can launch.</p>
        <p class="help-copy">Mouser's Order API supports cards saved in your Mouser account. AliExpress exposes a payment-attempt option for an authorized DS account. A saved card alone is not proof that your application/account can use it successfully; ordering, authorization and payment must be tested together. Keep cards on the supplier's own billing page. Never enter card numbers, CVV, bank details or email passwords in this admin.</p>
        <p class="help-copy">Supplier-sourced drafts default to “Fulfillment pending” and cannot be purchased. For stock you actually receive and ship yourself, choose office fulfillment in its product editor and set stock/rates in Orders. Existing digital, office and Printify checkout continues through Square.</p>
        <p><a href="https://www.mouser.com/en/api-order/" target="_blank" rel="noopener noreferrer">Mouser ordering & saved cards ↗</a> · <a href="https://printify.com/app/" target="_blank" rel="noopener noreferrer">Printify billing ↗</a> · <a href="https://openservice.aliexpress.com/" target="_blank" rel="noopener noreferrer">AliExpress API console ↗</a></p>
      </section>
      <section class="admin-section">
        <h2>Preferred suppliers</h2>
        <p class="help-copy">Bookmark stores such as Retro Castle with their exact official URL and a saved search such as “MiSTer FPGA”. Select the bookmark to restore your supplier and keywords, or open the store to browse its complete listings. Enter a numeric AliExpress Store ID to fill the URL automatically, or paste a /store/NUMBER URL to extract its ID. Use the store ID, not a product ID or seller member-account ID. Only listings you explicitly select become RODDY drafts.</p>
        <section v-for="(f, i) in preferences.favorites" :key="f.id" class="supplier-block">
          <div class="form-grid"><label>Preferred supplier name<input v-model="f.name" maxlength="100" /></label><label>Provider<select v-model="f.provider"><option value="mouser">Mouser</option><option value="aliexpress">AliExpress</option></select></label><label v-if="f.provider === 'aliexpress'">AliExpress Store ID<input v-model="f.storeId" inputmode="numeric" pattern="[0-9]{1,20}" maxlength="20" placeholder="912024455" @input="setStoreId(f)" /></label><label>Official store URL<input v-model="f.url" type="url" placeholder="https://www.aliexpress.com/store/…" @change="extractStoreId(f)" /></label><label>Saved keywords<input v-model="f.query" maxlength="160" placeholder="MiSTer FPGA" /></label></div>
          <button class="button small" @click="preferences.favorites.splice(i, 1)">Remove bookmark</button>
        </section>
        <div class="admin-actions"><button class="button small" :disabled="preferences.favorites.length >= 30" @click="addFavorite">Add preferred supplier</button><button class="button primary" @click="act(async () => { preferences = (await api('/preferences', preferences)).preferences; message = 'Preferred suppliers saved privately on your droplet.'; })">Save preferred suppliers</button></div>
        <label v-if="preferences.favorites.length">Use preferred supplier<select v-model="favoriteId" @change="chooseFavorite"><option value="">All suppliers / no seller restriction</option><option v-for="f in preferences.favorites" :key="f.id" :value="f.id">{{ f.name }}</option></select></label>
        <a v-if="favorite?.url?.startsWith('https://')" class="button small" :href="favorite.url" target="_blank" rel="noopener noreferrer">Open preferred supplier store ↗</a>
        <p v-if="favorite?.provider === 'aliexpress'" class="notice">AliExpress keyword search below searches the marketplace, not every listing in this store. Load product details to verify store ID {{ favorite.storeId || '(save an /store/NUMBER URL first)' }}; only matching seller listings can be imported while this preference is selected. For a complete seller catalog, use its store page or request an authorized seller feed. A search page is never represented as a complete store inventory.</p>
      </section>
      <section class="admin-section">
        <h2>Supplier API connection</h2>
        <label>Search provider<select v-model="provider"><option value="mouser">Mouser Electronics</option><option value="aliexpress">AliExpress</option></select></label>
        <p class="notice">{{ connection?.approvalPending ? 'Mouser key saved; supplier approval is pending. Website search is available; try the API after approval.' : connection?.searchVerifiedAt ? 'Search API access verified by a successful read.' : connection?.searchConfigured ? 'Credentials configured — verify by searching below.' : 'API credentials not configured yet. Website searches still work.' }} <span v-if="provider === 'aliexpress'">{{ connection?.buyerAuthorized ? 'Buyer token saved; permissions and expiry are checked by AliExpress on use.' : 'Buyer authorization is needed to load exact product variants.' }}</span></p>
        <template v-if="provider === 'mouser'"><p class="help-copy">Create/sign in to My Mouser, request Search API access, then enter its Search API key here. Search and ordering use separate permissions; this field does not connect an Order API key.</p><label>Mouser Search API key<input v-model="credentials.searchKey" type="password" autocomplete="off" placeholder="Leave blank to keep the saved key" /></label><a href="https://www.mouser.com/en/api-search/" target="_blank" rel="noopener noreferrer">Get Mouser Search API access ↗</a></template>
        <template v-else><p class="help-copy">Create an AliExpress Open Platform application with Dropship search/detail permissions. Enter its App Key and App Secret. Exact SKU details also need the buyer access token from its authorization flow. An affiliate-only key may not have these permissions. Account approval and token renewal are handled in AliExpress; rejected/expired access is reported here.</p><label>AliExpress App Key<input v-model="credentials.appKey" type="password" autocomplete="off" placeholder="Leave blank to keep saved" /></label><label>AliExpress App Secret<input v-model="credentials.appSecret" type="password" autocomplete="off" placeholder="Leave blank to keep saved" /></label><label>Authorized buyer access token<input v-model="credentials.accessToken" type="password" autocomplete="off" placeholder="Optional for search; required for product details" /></label></template>
        <p class="help-copy">Credentials are sent over HTTPS to your backend, stored in a private mode-600 file, and never returned to the browser or saved in the public catalog. Blank fields keep existing values. Save, then run a search to check access. Do not paste credentials in chat or GitHub.</p>
        <div class="admin-actions"><button class="button primary" @click="act(saveConnection)">Save private API connection</button><button class="button small" :disabled="!connection?.searchConfigured" @click="act(async () => { await api('/connections', {provider, disconnect: true}); await load(); results = null; message = 'Connection removed locally. Revoke its key in the supplier dashboard if needed.'; })">Disconnect this API</button></div>
      </section>
      <section class="admin-section">
        <h2>Search & inspect listings</h2>
        <div class="form-grid"><label>Keywords, part number, or product URL<input v-model="query" maxlength="2000" @keydown.enter.prevent="act(() => query.startsWith('https://') ? lookup(query) : search())" /></label><label>Ship-to market<select v-model="country" @change="results = null; selected = []"><option value="US">United States</option><option value="CA">Canada</option></select></label></div>
        <div class="admin-actions"><button class="button primary" :disabled="!connection?.searchConfigured || !query.trim()" @click="act(() => search())">Search supplier API</button><button class="button small" :disabled="!connection?.searchConfigured || !query.trim()" @click="act(() => lookup(query))">Load exact part / item URL</button><a class="button small" :href="websiteSearch" target="_blank" rel="noopener noreferrer">Search supplier website ↗</a></div>
        <p class="help-copy">Mouser: search keywords or load an exact Mouser part number. AliExpress: search keywords, then load a result to choose its exact variant and verify the seller. You can also paste an official /item/NUMBER.html URL or numeric product ID. Currency is USD where returned; unknown prices or stock remain unknown. Current search results are cached for five minutes to respect API quotas.</p>
        <p v-if="results">Page {{ page }} · {{ results.total ?? 'Unknown total' }} matches · {{ results.cached ? 'Cached result' : 'API result' }} · checked {{ new Date(results.checkedAt * 1000).toLocaleString() }}. {{ provider === 'mouser' ? 'Mouser pricing follows the API account’s market; Canadian landed costs still need a shipping quote.' : 'Promotional and variant prices can change; search prices are indicative.' }}</p>
        <div v-if="rows.length" class="admin-actions"><button class="button small" @click="selected = rows.filter(eligible).map(r => r.sku)">Select all eligible results on this page</button><button class="button small" @click="selected = []; review = false">Clear selection</button></div>
        <section v-for="row in rows" :key="row.sku" class="supplier-block">
          <div class="supplier-result"><img v-if="row.image" :src="row.image" :alt="row.name" loading="lazy" /><div><h3>{{ row.name }}</h3><p>{{ row.manufacturer }} {{ row.manufacturerPartNumber }} · {{ row.sku }}</p><p>Supplier price: {{ dollars(chosen(row)?.costCents ?? row.costCents) }} · Stock: {{ chosen(row)?.availableQuantity ?? row.availableQuantity ?? 'Unknown' }} · Minimum {{ row.minimumQuantity }} · Order multiple {{ row.orderMultiple }}</p><p>{{ row.availability }} {{ row.leadTime ? `· Lead time: ${row.leadTime}` : '' }}</p><p v-if="row.sellerName">Seller: {{ row.sellerName }} · Store ID {{ row.sellerId }}</p><p v-if="row.restriction" class="notice">{{ row.restriction }}</p></div></div>
          <label v-if="row.variants?.length">Exact supplier variant<select v-model="variants[row.sku]" @change="selected = selected.filter(s => s !== row.sku)"><option value="">Choose variant…</option><option v-for="v in row.variants" :key="v.id" :value="v.id">{{ v.label || v.id }} · {{ dollars(v.costCents) }} · stock {{ v.availableQuantity ?? 'unknown' }}</option></select></label>
          <p v-if="favorite && !sellerMatches(row)" class="notice">Seller not verified as the preferred store. Load details; a different seller cannot be imported under this preference.</p>
          <div class="admin-actions"><label class="check"><input v-model="selected" :value="row.sku" type="checkbox" :disabled="!eligible(row)" />Select for import</label><button class="button small" @click="act(() => lookup(row.sku, row))">Load / refresh details</button><a v-if="row.url" :href="row.url" target="_blank" rel="noopener noreferrer" class="button small">Supplier listing ↗</a><a v-if="row.datasheet" :href="row.datasheet" target="_blank" rel="noopener noreferrer" class="button small">Datasheet ↗</a><button v-if="existing(row)" class="button small" @click="emit('edit-product', existing(row))">Already in RODDY — edit</button></div>
        </section>
        <p v-if="results && !rows.length">No products returned. Try another query or browse the supplier website.</p>
        <div v-if="results" class="admin-actions"><button class="button small" :disabled="page <= 1" @click="act(() => search(page - 1))">Previous results</button><button class="button small" :disabled="!results.hasMore" @click="act(() => search(page + 1))">More results</button><button class="button primary" :disabled="!selection.length" @click="review = true">Review {{ selection.length }} selected import(s)</button></div>
      </section>
      <section class="admin-section">
        <h2>Import prices & profit estimate</h2>
        <p class="help-copy">These are draft price estimates, not guaranteed profits or live shipping quotes. The shipping allowance, processing fee estimate, supplier taxes, duties, currency conversion and returns all affect the actual profit. Verify your Square account rate. Editing these estimates does not change existing products.</p>
        <div class="form-grid"><label>Department<select v-model="category"><option v-for="c in catalog.categories" :key="c.id" :value="c.id">{{ c.name }}</option></select></label><label>Pricing method<select v-model="rules.mode"><option value="markup">Markup on estimated landed cost</option><option value="margin">Target margin after estimated fees</option></select></label><label>{{ rules.mode === 'margin' ? 'Target margin %' : 'Markup %' }}<input v-model.number="rules.percent" type="number" min="0" max="500" step=".01" /></label><label>Shipping / duties allowance per unit (USD)<input v-model.number="rules.shippingBuffer" type="number" min="0" step=".01" /></label><label>Minimum estimated profit per unit (USD)<input v-model.number="rules.minimumProfit" type="number" min="0" step=".01" /></label><label>Estimated Square processing %<input v-model.number="rules.feePercent" type="number" min="0" max="99" step=".01" /></label><label>Estimated fixed processing fee (USD)<input v-model.number="rules.feeFixed" type="number" min="0" step=".01" /></label></div><label class="check"><input v-model="rules.round99" type="checkbox" />Round estimated retail prices up to .99</label>
      </section>
      <section v-if="review" class="admin-section">
        <h2>Review before adding hidden drafts</h2>
        <p>Only these {{ selection.length }} selected listings will be added. Nothing is purchased or published. Unknown costs require manual pricing.</p>
        <div class="supplier-table"><table><thead><tr><th>Listing</th><th>Proposed retail</th><th>Estimated profit / unit</th></tr></thead><tbody><tr v-for="row in selection" :key="row.sku"><td>{{ row.name }} {{ chosen(row)?.label }}</td><td>{{ estimate(row) ? '$' + estimate(row).retail.toFixed(2) : 'Manual pricing / check rules' }}</td><td>{{ estimate(row) ? '$' + estimate(row).profit.toFixed(2) : 'Unknown' }}</td></tr></tbody></table></div>
        <button class="button primary" :disabled="!selection.length" @click="act(importSelected)">Add selected as hidden product drafts</button>
      </section>
    </fieldset>
  </div>
</template>
<style scoped>
.supplier-manager fieldset{border:0;padding:0;min-width:0}.supplier-manager p{line-height:1.65}.supplier-manager a{text-decoration:underline}.supplier-block{border:1px solid var(--rule);padding:18px;margin:16px 0}.supplier-result{display:flex;gap:20px}.supplier-result>img{width:100px;height:100px;object-fit:contain;flex-shrink:0;background:white}.supplier-result>div{min-width:0;overflow-wrap:anywhere}.supplier-table{overflow:auto}.supplier-table table{width:100%;border-collapse:collapse}.supplier-table th,.supplier-table td{padding:14px;text-align:left;border-bottom:1px solid var(--rule)}@media(max-width:600px){.supplier-result{flex-direction:column}.supplier-block{padding:12px}}
</style>
