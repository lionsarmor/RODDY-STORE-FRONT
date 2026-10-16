<script setup>
import KitCarts from './KitCarts.vue';
import PricingManager from './PricingManager.vue';
import { computed, nextTick, reactive, ref, watch } from 'vue';
import SupplierDirectory from './SupplierDirectory.vue';
import { commerceRequest } from './commerce-api';
import { priceEstimate, supplierDraft, supplierIdentity } from './supplier-model';
const props = defineProps({catalog: Object, token: String, connected: Boolean});
const emit = defineEmits(['import-products', 'edit-product', 'navigate']);
const state = ref(null);
const preferences = ref({favorites: [], revision: 1});
const credentials = reactive({searchKey: '', orderKey:'', appKey: '', appSecret: '', accessToken: ''});
const provider = ref('mouser');
const query = ref('');
const country = ref('US');
const page = ref(1);
const results = ref(null);
const selected = ref([]);
const variants = reactive({});
const itemErrors = reactive({});
const loadingItem = ref('');
const optionInputs = {};
let optionToFocus = '';
const favoriteId = ref('');
const category = ref(props.catalog.categories[0]?.id || '');
const review = ref(false);
const reviewPanel = ref(null);
const busy = ref(false);
const error = ref('');
const message = ref('');
const authorizationUrl = ref('');
const checks=ref(null);
const connectionsPanel = ref(null);
let initialized = false;
const rules = reactive({mode: 'markup', percent: 30, minimumProfit: 5, shippingBuffer: 15, feePercent: 2.9, feeFixed: .30, round99: true});
const favorite = computed(() => preferences.value.favorites.find(f => f.id === favoriteId.value));
const connection = computed(() => state.value?.connections.find(c => c.provider === provider.value));
const websiteSearch = computed(() => provider.value === 'mouser' ? `https://www.mouser.com/c/?q=${encodeURIComponent(query.value)}` : `https://www.aliexpress.com/w/wholesale-${encodeURIComponent(query.value.replaceAll(' ', '-'))}.html`);
const rows = computed(() => results.value?.products || []);
const selection = computed(() => rows.value.filter(row => selected.value.includes(row.sku)));
const readySelection = computed(() => selection.value.filter(eligible));
const api = (path, body) => commerceRequest(props.catalog.settings.checkoutEndpoint, '/admin/suppliers' + path, props.token, body);
async function act(fn) {
  if (busy.value) return;
  busy.value = true; error.value = ''; message.value = '';
  try { await fn(); } catch (e) { error.value = e.message; }
  finally {
    busy.value = false;
    await nextTick();
    optionInputs[optionToFocus]?.focus(); optionToFocus = '';
  }
}
async function load() {
  state.value = await api(''); preferences.value = JSON.parse(JSON.stringify(state.value.preferences)); authorizationUrl.value = '';
  if (!initialized) {
    if (state.value.connections.some(c => c.provider === 'aliexpress' && c.buyerAuthorized)) provider.value = 'aliexpress';
    favoriteId.value = ''; initialized = true;
  }
}
watch(() => [props.connected, props.token], async () => {
  state.value = null; results.value = null; selected.value = [];
  initialized = false; favoriteId.value = '';
  Object.keys(credentials).forEach(key => credentials[key] = '');
  if (props.connected) await act(load);
}, {immediate: true});
watch(provider, () => { if (favorite.value && favorite.value.provider !== provider.value) favoriteId.value = ''; results.value = null; selected.value = []; review.value = false; authorizationUrl.value = ''; Object.keys(credentials).forEach(key => credentials[key] = ''); });
async function authorizeBuyer() {
  const result = await api('/aliexpress/authorize', {});
  const url = new URL(result.url);
  if (url.origin !== new URL(props.catalog.settings.checkoutEndpoint).origin || url.protocol !== 'https:' || url.pathname !== '/suppliers/aliexpress/authorize' || !/^[A-Za-z0-9_-]{43}$/.test(url.searchParams.get('ticket') || '')) throw new Error('Invalid authorization destination.');
  authorizationUrl.value = url.href;
  message.value = 'Open Continue to AliExpress below within 10 minutes. Sign in on AliExpress, approve access, then return here and reload supplier settings. Your password stays on AliExpress.';
}
function setStoreId(f) { if (/^\d{1,20}$/.test(f.storeId || '')) f.url = `https://www.aliexpress.com/store/${f.storeId}`; }
function extractStoreId(f) { try { const match = new URL(f.url).pathname.match(/\/store\/(\d+)/); f.storeId = match?.[1] || ''; } catch { f.storeId = ''; } }
function addFavorite() { preferences.value.favorites.push({id: crypto.randomUUID(), name: '', provider: 'aliexpress', storeId: '', url: '', query: 'MiSTer FPGA'}); }
function chooseFavorite() {
  selected.value = []; review.value = false;
  if (!favorite.value) return;
  provider.value = favorite.value.provider;
  query.value = favorite.value.query || '';
  results.value = null; selected.value = [];
}
async function saveConnection() {
  try { await api('/connections', {provider: provider.value, ...credentials}); await load(); message.value = 'Credentials saved privately. Run a search to verify access. Set each product’s fulfillment mode separately; all orders remain visible in Orders.'; }
  finally { Object.keys(credentials).forEach(key => credentials[key] = ''); }
}
async function search(next = 1) {
  results.value = await api('/search', {provider: provider.value, query: query.value, country: country.value, page: next});
  page.value = next; selected.value = []; review.value = false;
  state.value = await api('');
  results.value.products = results.value.products.map(row => ({...row, checkedAt: results.value.checkedAt}));
  Object.keys(itemErrors).forEach(key => delete itemErrors[key]);
}
async function lookup(value, existingRow) {
  const sku = existingRow?.sku || value;
  loadingItem.value = sku; delete itemErrors[sku];
  try {
    const data = await api('/product', {provider: provider.value, query: value, country: country.value});
    const row = {...data.product, checkedAt: data.checkedAt, detailsLoaded: true};
    if (row.variants?.length === 1) variants[row.sku] = row.variants[0].id;
    if (!results.value) results.value = {products: [], hasMore: false, checkedAt: data.checkedAt};
    const i = rows.value.findIndex(r => r.sku === (existingRow?.sku || row.sku));
    if (i < 0) results.value.products.unshift(row); else results.value.products.splice(i, 1, row);
    message.value = `${row.name}: supplier details loaded. Review stock, minimum quantity and variant before importing.`;
    return row;
  } catch (e) {
    itemErrors[sku] = e.message;
    throw e;
  } finally { loadingItem.value = ''; }
}
function chosen(row) { return row.variants?.find(v => v.id === variants[row.sku]); }
function existing(row) { return props.catalog.products.find(p => p.supplier && supplierIdentity(p) === supplierIdentity({...row, variantId: variants[row.sku] || ''})); }
function sellerMatches(row) { return !favorite.value || favorite.value.provider !== 'aliexpress' || (!!favorite.value.storeId && row.sellerId === favorite.value.storeId); }
function selectable(row) { return !!row.sku && !existing(row) && (!row.sellerId || sellerMatches(row)); }
function eligible(row) { return !!row.sku && !existing(row) && sellerMatches(row) && (row.provider !== 'aliexpress' || !!chosen(row)); }
function needsDetails(row) { return row.provider === 'aliexpress' && !row.variants?.length && !row.detailsLoaded; }
function importIssue(row) {
  if (itemErrors[row.sku]) return itemErrors[row.sku];
  if (existing(row)) return 'This exact option is already in your catalog. Edit it or choose a different option.';
  if (favorite.value && !sellerMatches(row)) return row.sellerId ? 'This seller does not match your filter. Choose All suppliers to import it.' : 'Load details to verify this seller.';
  if (needsDetails(row)) return 'Load options to finish preparing this item.';
  if (row.provider === 'aliexpress' && !row.variants?.length) return 'The supplier returned no exact options. Retry loading details or choose another listing.';
  if (row.provider === 'aliexpress' && !chosen(row)) return 'Choose an exact option below before adding the draft.';
  return '';
}
function focusOptions(row) { optionToFocus = row.sku; }
async function openReview() { review.value = true; await nextTick(); reviewPanel.value?.scrollIntoView({block: 'start'}); }
async function toggleSelection(row, checked) {
  review.value = false;
  if (!checked) { selected.value = selected.value.filter(s => s !== row.sku); return; }
  selected.value = [...new Set([...selected.value, row.sku])];
  if (needsDetails(row)) {
    await act(async () => { row = await lookup(row.sku, row); focusOptions(row); });
  }
}
function chooseVariant(row) {
  delete itemErrors[row.sku];
  if (!selectable(row)) selected.value = selected.value.filter(s => s !== row.sku);
}
function estimate(row) { try { return priceEstimate(chosen(row)?.costCents ?? row.costCents, rules); } catch { return null; } }
function dollars(cents) { return Number.isInteger(cents) ? `$${(cents / 100).toFixed(2)}` : 'Unknown'; }
async function addAndEdit(row) {
  if (row.provider === 'aliexpress' && !row.variants?.length) row = await lookup(row.sku, row);
  if (!eligible(row)) {
    itemErrors[row.sku] = importIssue(row);
    focusOptions(row);
    return;
  }
  if (!props.catalog.categories.some(c => c.id === category.value)) throw new Error('Choose a storefront department.');
  const draft = supplierDraft(row, variants[row.sku], category.value, rules, props.catalog.products);
  emit('import-products', [draft]);
  emit('edit-product', draft);
  selected.value = selected.value.filter(s => s !== row.sku);
  message.value = 'Item added to your product draft. Edit its department, tags, descriptions, pictures and price, then Publish when ready.';
}
function importSelected() {
  const drafts = [], failures = [];
  if (!selection.value.length || readySelection.value.length !== selection.value.length) throw new Error('Finish choosing options for every selected item in the review below.');
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
    <SupplierDirectory :endpoint="catalog.settings.checkoutEndpoint" :token="token" :connected="connected" @navigate="emit('navigate', $event)" @connection="async p => { provider=p; await nextTick(); connectionsPanel.open=true; connectionsPanel.scrollIntoView({block:'start'}); }" />
    <section class="admin-section">
      <p class="eyebrow">DISCOVER · CHOOSE · REVIEW · PUBLISH</p>
      <h2>Suppliers & product imports</h2>
      <p>Search for an item and select it for import, or use Choose options & add. Options load automatically for individual selections. Choose the exact option, then open the normal product editor for departments, tags, descriptions, pictures and pricing.</p>
      <p v-if="!connected" class="notice">Connect to GitHub above to manage supplier connections and private search results.</p>
      <button class="button small" :disabled="!connected || busy" @click="act(load)">Reload supplier settings</button>
      <p v-if="error" class="form-error" role="alert" style="white-space:pre-wrap">{{ error }}</p><p v-if="message" class="notice" role="status">{{ message }}</p>
    </section>
    <fieldset v-if="connected && state" :disabled="busy">
      <section class="admin-section">
        <h2>Search & inspect listings</h2>
        <div class="form-grid"><label>Search provider<select v-model="provider" aria-label="Search provider"><option value="aliexpress">AliExpress</option><option value="mouser">Mouser Electronics</option></select></label><label>Seller filter<select v-model="favoriteId" aria-label="Seller filter" @change="chooseFavorite"><option value="">All suppliers / no seller restriction</option><option v-for="f in preferences.favorites.filter(f => f.provider === provider)" :key="f.id" :value="f.id">{{ f.name }}</option></select></label><label>Keywords, part number, or product URL<input v-model="query" maxlength="2000" placeholder="Search an item or paste its product URL" @keydown.enter.prevent="act(() => query.startsWith('https://') ? lookup(query) : search())" /></label><label>Ship-to market<select v-model="country" @change="results = null; selected = []"><option value="US">United States</option><option value="CA">Canada</option></select></label><label>Department for new items<select v-model="category" aria-label="Department for new items"><option v-for="c in catalog.categories" :key="c.id" :value="c.id">{{ c.name }}</option></select></label></div>
        <p class="help-copy">{{ favorite ? `Only verified listings from ${favorite.name} can be added.` : 'All suppliers selected. Search and add individual listings from any seller.' }} <button v-if="favorite" class="button small" @click="favoriteId = ''; chooseFavorite()">Search all suppliers</button></p>
        <p class="help-copy">{{ connection?.searchVerifiedAt ? 'Supplier API verified.' : connection?.searchConfigured ? 'API credentials saved. Run a search to check current access.' : 'Connect this supplier to use API search.' }} <span v-if="connection?.approvalPending">Mouser approval has not been verified by a successful API read.</span> <button class="button small" @click="connectionsPanel.open = true; connectionsPanel.scrollIntoView({block: 'start'})">Manage API connection</button></p>
        <p v-if="provider === 'mouser' && connection?.orderKeyStored && !connection?.searchConfigured" class="notice">Your Order/Cart API key is saved separately{{ connection.orderApprovalPending ? ' and its approval is pending' : '' }}. Product searches need a different Search API key. Request Search API access below, then save that key in Supplier connections.</p>
        <div class="admin-actions"><button class="button primary" :disabled="!connection?.searchConfigured || !query.trim()" @click="act(() => search())">Search supplier API</button><button class="button small" :disabled="!connection?.searchConfigured || !query.trim()" @click="act(() => lookup(query))">Load exact part / item URL</button><a class="button small" :href="websiteSearch" target="_blank" rel="noopener noreferrer">Search supplier website ↗</a></div>
        <p class="help-copy">Mouser: search keywords or load an exact Mouser part number. AliExpress: select a result to load its exact options and verify the seller. You can also paste an official /item/NUMBER.html URL or numeric product ID. Currency is USD where returned; unknown prices or stock remain unknown. Current search results are cached for five minutes to respect API quotas.</p>
        <p v-if="results">Page {{ page }} · {{ results.total ?? 'Unknown total' }} matches · {{ results.cached ? 'Cached result' : 'API result' }} · checked {{ new Date(results.checkedAt * 1000).toLocaleString() }}. {{ provider === 'mouser' ? 'Mouser pricing follows the API account’s market; Canadian landed costs still need a shipping quote.' : 'Promotional and variant prices can change; search prices are indicative.' }}</p>
        <div v-if="rows.length" class="admin-actions"><button class="button small" @click="selected = rows.filter(selectable).map(r => r.sku); review = false">Select results on this page</button><button class="button small" @click="selected = []; review = false">Clear selection</button><button class="button primary" :disabled="!selection.length" @click="openReview">Review selection ({{ selection.length }})</button></div>
        <section v-for="row in rows" :key="row.sku" class="supplier-block">
          <div class="supplier-result"><img v-if="row.image" :src="row.image" :alt="row.name" loading="lazy" /><div><h3>{{ row.name }}</h3><p>{{ row.manufacturer }} {{ row.manufacturerPartNumber }} · {{ row.sku }}</p><p>Supplier price: {{ dollars(chosen(row)?.costCents ?? row.costCents) }} · Stock: {{ chosen(row)?.availableQuantity ?? row.availableQuantity ?? 'Unknown' }} · Minimum {{ row.minimumQuantity }} · Order multiple {{ row.orderMultiple }}</p><p>{{ row.availability }} {{ row.leadTime ? `· Lead time: ${row.leadTime}` : '' }}</p><p v-if="row.sellerName">Seller: {{ row.sellerName }} · Store ID {{ row.sellerId }}</p><p v-if="row.restriction" class="notice">{{ row.restriction }}</p></div></div>
          <label v-if="row.variants?.length">Exact supplier variant<select :ref="el => { optionInputs[row.sku] = el; }" v-model="variants[row.sku]" aria-label="Exact supplier variant" @change="chooseVariant(row)"><option value="">Choose variant…</option><option v-for="v in row.variants" :key="v.id" :value="v.id">{{ v.label || v.id }} · {{ dollars(v.costCents) }} · stock {{ v.availableQuantity ?? 'unknown' }}</option></select></label>
          <p v-if="favorite && !sellerMatches(row)" class="notice">Seller not verified as the preferred store. Load details; a different seller cannot be imported under this preference.</p>
          <p v-if="estimate(row)" class="help-copy">Estimated retail ${{ estimate(row).retail.toFixed(2) }} · estimated profit ${{ estimate(row).profit.toFixed(2) }} per item using your pricing rules. Confirm actual shipping and fees before selling.</p>
          <p v-if="loadingItem === row.sku" class="notice" role="status">Loading this item's options and seller details…</p>
          <p v-else-if="itemErrors[row.sku]" class="form-error" role="alert">{{ itemErrors[row.sku] }}</p>
          <p v-else-if="!eligible(row)" class="help-copy">{{ needsDetails(row) ? 'Select for import or choose options below to load this listing.' : importIssue(row) }}</p>
          <p v-if="selected.includes(row.sku)" class="help-copy">{{ eligible(row) ? 'Selected and ready for import review.' : 'Selected — finish preparing its exact option before adding a draft.' }}</p>
          <div class="admin-actions">
            <button v-if="!existing(row)" class="button primary" :disabled="!selectable(row)" @click="act(() => addAndEdit(row))">{{ row.provider === 'aliexpress' && !row.variants?.length ? row.detailsLoaded ? 'Retry loading options' : 'Choose options & add' : row.provider === 'aliexpress' && !chosen(row) ? 'Choose an option above' : 'Add & edit product' }}</button>
            <button v-else class="button small" @click="emit('edit-product', existing(row))">Already in RODDY — edit</button>
            <button class="button small" @click="act(() => lookup(row.sku, row))">Load / refresh details</button>
            <a v-if="row.url" :href="row.url" target="_blank" rel="noopener noreferrer" class="button small">Supplier listing ↗</a>
            <a v-if="row.datasheet" :href="row.datasheet" target="_blank" rel="noopener noreferrer" class="button small">Datasheet ↗</a>
            <label class="check"><input :checked="selected.includes(row.sku)" type="checkbox" :disabled="!selected.includes(row.sku) && !selectable(row)" @change="toggleSelection(row, $event.target.checked)" />Select for import</label>
          </div>
        </section>
        <p v-if="results && !rows.length">No products returned. Try another query or browse the supplier website.</p>
        <div v-if="results" class="admin-actions"><button class="button small" :disabled="page <= 1" @click="act(() => search(page - 1))">Previous results</button><button class="button small" :disabled="!results.hasMore" @click="act(() => search(page + 1))">More results</button><button class="button primary" :disabled="!selection.length" @click="openReview">Review {{ selection.length }} selected import(s)</button></div>
      </section>
      <section v-if="review" ref="reviewPanel" class="admin-section supplier-review">
        <h2>Review before adding hidden drafts</h2>
        <p>{{ readySelection.length }} of {{ selection.length }} selected listings ready. Finish each item's options below or remove it from this selection. Page selection loads options one item at a time so it does not exhaust supplier API limits. Nothing is purchased or published. Unknown costs require manual pricing.</p>
        <div class="supplier-table"><table><thead><tr><th>Listing & exact option</th><th>Proposed retail</th><th>Estimated profit / unit</th></tr></thead><tbody><tr v-for="row in selection" :key="row.sku"><td>
          <strong>{{ row.name }}</strong>
          <p v-if="importIssue(row)" :class="itemErrors[row.sku] ? 'form-error' : 'help-copy'">{{ importIssue(row) }}</p>
          <label v-if="row.variants?.length">Exact supplier variant<select v-model="variants[row.sku]" aria-label="Exact supplier variant" @change="chooseVariant(row)"><option value="">Choose variant…</option><option v-for="v in row.variants" :key="v.id" :value="v.id">{{ v.label || v.id }} · {{ dollars(v.costCents) }} · stock {{ v.availableQuantity ?? 'unknown' }}</option></select></label>
          <button v-if="needsDetails(row) || itemErrors[row.sku] || row.provider === 'aliexpress' && !row.variants?.length" class="button small" @click="act(() => lookup(row.sku, row))">{{ itemErrors[row.sku] || row.detailsLoaded ? 'Retry loading options' : 'Load options' }}</button>
          <button class="button small" @click="selected = selected.filter(s => s !== row.sku)">Remove from selection</button>
        </td><td>{{ estimate(row) ? '$' + estimate(row).retail.toFixed(2) : 'Manual pricing / check rules' }}</td><td>{{ estimate(row) ? '$' + estimate(row).profit.toFixed(2) : 'Unknown' }}</td></tr></tbody></table></div>
        <p v-if="selection.length && readySelection.length !== selection.length" class="notice">Choose the missing options above before adding these drafts.</p>
        <button class="button primary" :disabled="!selection.length || readySelection.length !== selection.length" @click="act(importSelected)">Add selected as hidden product drafts</button>
      </section>
      <details class="supplier-settings"><summary>Kit carts · reusable revision BOMs</summary><KitCarts v-if="connected" :catalog="catalog" :token="token" /></details>
      <details class="supplier-settings" open><summary>Automatic retail pricing & live price status</summary><PricingManager v-if="connected" :endpoint="catalog.settings.checkoutEndpoint" :token="token" :catalog="catalog" /></details>
      <details class="supplier-settings"><summary>Draft import price estimates</summary>
      <section class="admin-section">
        <h2>Import prices & profit estimate</h2>
        <p class="help-copy">These are draft price estimates, not guaranteed profits or live shipping quotes. The shipping allowance, processing fee estimate, supplier taxes, duties, currency conversion and returns all affect the actual profit. Verify your Square account rate. Editing these estimates does not change existing products.</p>
        <div class="form-grid"><label>Pricing method<select v-model="rules.mode"><option value="markup">Markup on estimated landed cost</option><option value="margin">Target margin after estimated fees</option></select></label><label>{{ rules.mode === 'margin' ? 'Target margin %' : 'Markup %' }}<input v-model.number="rules.percent" type="number" min="0" max="500" step=".01" /></label><label>Shipping / duties allowance per unit (USD)<input v-model.number="rules.shippingBuffer" type="number" min="0" step=".01" /></label><label>Minimum estimated profit per unit (USD)<input v-model.number="rules.minimumProfit" type="number" min="0" step=".01" /></label><label>Estimated Square processing %<input v-model.number="rules.feePercent" type="number" min="0" max="99" step=".01" /></label><label>Estimated fixed processing fee (USD)<input v-model.number="rules.feeFixed" type="number" min="0" step=".01" /></label></div><label class="check"><input v-model="rules.round99" type="checkbox" />Round estimated retail prices up to .99</label>
      </section>
      </details>
      <details class="supplier-settings" ref="connectionsPanel"><summary>Supplier connections & credentials</summary>
      <section class="admin-section">
        <h2>Supplier API connection</h2>
        <p class="notice">{{ connection?.approvalPending ? 'Mouser key saved and marked pending; a successful API search has not verified approval. Run a search for the current provider response.' : connection?.searchVerifiedAt ? 'Search API access verified by a successful read.' : connection?.searchConfigured ? 'Credentials configured — verify by searching below.' : 'API credentials not configured yet. Website searches still work.' }} <span v-if="provider === 'aliexpress'">{{ connection?.buyerAuthorized ? 'Buyer token saved; verify permissions with an exact product lookup.' : 'Buyer authorization is needed to load exact product variants.' }}</span></p>
        <template v-if="provider === 'mouser'"><p class="help-copy">Create/sign in to My Mouser. Under the separate Search API section, choose Learn More and request Search API access. Enter the resulting Search API key here. A key described as “Order API and Cart API” cannot be used for searches; approval of those APIs does not activate Search API.</p><p v-if="connection?.orderKeyStored" class="help-copy">Your Order/Cart key is retained privately. {{ connection.orderVerifiedAt ? 'Order API access verified.' : connection.orderApprovalPending ? 'Approval has not yet been verified.' : 'Verify the connection to check access.' }} {{ connection.automaticOrdering ? 'Automatic ordering is enabled for products set to automatic fulfillment.' : 'Automatic purchasing is disabled.' }}</p><p v-if="connection?.orderReadiness" class="notice">{{ connection.orderReadiness.message }} <span v-if="connection.orderReadiness.checkedAt">Checked {{ new Date(connection.orderReadiness.checkedAt * 1000).toLocaleString() }}.</span> <a href="https://www.mouser.com/MyMouser/ManageSaveCards.aspx" target="_blank" rel="noopener noreferrer">Manage saved cards on Mouser ↗</a></p><div class="admin-actions"><button class="button small" @click="act(async()=>{await api('/mouser/automation',{enabled:!connection?.automaticOrdering});await load();})">{{ connection?.automaticOrdering ? 'Disable automatic Mouser ordering' : 'Enable automatic Mouser ordering' }}</button></div><p class="help-copy">Automatic Mouser orders use the customer delivery address and the lowest quoted prepaid carrier rate. Automatic pricing follows your saved markup rules; paid totals are preserved. Cost overruns suspend new purchases for review. Existing manual orders remain manual. AliExpress and Yuzu automation are not connected yet.</p><label>Mouser Order/Cart API key<input v-model="credentials.orderKey" type="password" autocomplete="off" placeholder="Leave blank to keep the saved Order/Cart key" /></label><label>Mouser Search API key<input v-model="credentials.searchKey" type="password" autocomplete="off" placeholder="Paste the separate Search API key" /></label><a href="https://www.mouser.com/en/api-search/" target="_blank" rel="noopener noreferrer">Get Mouser Search API access ↗</a></template>
        <template v-else>
          <p class="help-copy">Developer review approval lets you proceed with application setup. In AliExpress App Console, choose the active Drop Shipping category and Create App. Name it RODDY Store and request search and product-detail permissions. Commercial Developer, Self-Developer and Affiliates API are different categories. Save its App Key and App Secret here, then authorize the buyer account you will use for sourcing.</p>
          <p class="help-copy">In the application settings, set this exact callback URL:</p><code class="supplier-callback">{{ connection?.callbackUrl || 'Backend HTTPS public URL needs configuration.' }}</code>
          <label>AliExpress App Key<input v-model="credentials.appKey" type="password" autocomplete="off" placeholder="Leave blank to keep saved" /></label><label>AliExpress App Secret<input v-model="credentials.appSecret" type="password" autocomplete="off" placeholder="Leave blank to keep saved" /></label>
          <details><summary>Advanced: manually supplied buyer token</summary><p class="help-copy">Prefer the authorization button below so the server can securely store and renew both tokens. A manually entered token has no automatic refresh unless you authorize again.</p><label>Authorized buyer access token<input v-model="credentials.accessToken" type="password" autocomplete="off" placeholder="Leave blank to use browser authorization" /></label></details>
          <p v-if="connection?.accessExpiresAt" class="help-copy">Buyer access expires: {{ new Date(connection.accessExpiresAt * 1000).toLocaleString() }}. {{ connection.refreshAvailable ? 'The server checks for renewal every five minutes, including when the store is quiet.' : 'Authorize again to keep stock and shipping checks connected.' }}</p>
          <p v-if="connection?.refreshExpiresAt" class="help-copy">Renewal permission ends: {{ new Date(connection.refreshExpiresAt * 1000).toLocaleString() }}. Use “Authorize AliExpress buyer” before then to keep automatic renewal available. Renewing access does not extend this permission.</p>
        </template>
        <p class="help-copy">Credentials are sent over HTTPS to your backend, stored in a private mode-600 file, and never returned to the browser or saved in the public catalog. Blank fields keep existing values. Save, then run a search to check access. Do not paste credentials in chat or GitHub.</p>
        <div v-if="checks" class="notice"><p v-for="(check,name) in checks" :key="name">{{name}}: {{check.ok?'API access verified':check.message}}<span v-if="check.paymentMethods!==undefined"> · {{check.paymentMethods}} payment methods · {{check.shippingMethods}} shipping methods</span><span v-if="check.ok && check.message"> · {{check.message}}</span></p></div><div class="admin-actions"><button class="button small" @click="act(async()=>{const result=await api('/verify',{provider});checks=result.checks;await load();})">Verify supplier connection</button><button class="button primary" @click="act(saveConnection)">Save private API connection</button><button class="button small" :disabled="!connection?.searchConfigured" @click="act(async () => { await api('/connections', {provider, disconnect: true}); await load(); results = null; message = 'Connection removed locally. Revoke its key in the supplier dashboard if needed.'; })">Disconnect this API</button></div>
        <div v-if="provider === 'aliexpress'" class="admin-actions"><button class="button small" :disabled="!connection?.searchConfigured || !connection?.callbackUrl" @click="act(authorizeBuyer)">Authorize AliExpress buyer</button><a v-if="authorizationUrl" class="button primary" :href="authorizationUrl" target="_blank" rel="noopener noreferrer">Continue to AliExpress ↗</a><button class="button small" :disabled="!connection?.refreshAvailable" @click="act(async () => { await api('/aliexpress/refresh', {}); await load(); message = 'Buyer authorization renewed privately. Run an exact product lookup to verify permissions.'; })">Renew buyer authorization</button></div>
      </section>
      </details>
      <details class="supplier-settings"><summary>Manage preferred supplier bookmarks</summary>
      <section class="admin-section">
        <h2>Preferred suppliers</h2>
        <p class="help-copy">Bookmark stores such as Retro Castle with their exact official URL and a saved search such as “MiSTer FPGA”. Select the bookmark to restore your supplier and keywords, or open the store to browse its complete listings. Enter a numeric AliExpress Store ID to fill the URL automatically, or paste a /store/NUMBER URL to extract its ID. Use the store ID, not a product ID or seller member-account ID. Only listings you explicitly select become RODDY drafts.</p>
        <section v-for="(f, i) in preferences.favorites" :key="f.id" class="supplier-block">
          <div class="form-grid"><label>Preferred supplier name<input v-model="f.name" maxlength="100" /></label><label>Provider<select v-model="f.provider"><option value="mouser">Mouser</option><option value="aliexpress">AliExpress</option></select></label><label v-if="f.provider === 'aliexpress'">AliExpress Store ID<input v-model="f.storeId" inputmode="numeric" pattern="[0-9]{1,20}" maxlength="20" placeholder="912024455" @input="setStoreId(f)" /></label><label>Official store URL<input v-model="f.url" type="url" placeholder="https://www.aliexpress.com/store/…" @change="extractStoreId(f)" /></label><label>Saved keywords<input v-model="f.query" maxlength="160" placeholder="MiSTer FPGA" /></label></div>
          <button class="button small" @click="preferences.favorites.splice(i, 1)">Remove bookmark</button>
        </section>
        <div class="admin-actions"><button class="button small" :disabled="preferences.favorites.length >= 30" @click="addFavorite">Add preferred supplier</button><button class="button primary" @click="act(async () => { preferences = (await api('/preferences', preferences)).preferences; message = 'Preferred suppliers saved privately on your droplet.'; })">Save preferred suppliers</button></div>
        <a v-if="favorite?.url?.startsWith('https://')" class="button small" :href="favorite.url" target="_blank" rel="noopener noreferrer">Open preferred supplier store ↗</a>
        <p v-if="favorite?.provider === 'aliexpress'" class="notice">AliExpress keyword search below searches the marketplace, not every listing in this store. Load product details to verify store ID {{ favorite.storeId || '(save an /store/NUMBER URL first)' }}; only matching seller listings can be imported while this preference is selected. For a complete seller catalog, use its store page or request an authorized seller feed. A search page is never represented as a complete store inventory.</p>
      </section>
      </details>
      <details class="supplier-settings"><summary>How payments and fulfillment work</summary>
      <section class="admin-section">
        <h2>How payments and fulfillment work</h2>
        <p><strong>Customer → RODDY through Square → your payout bank.</strong> The supplier charges your separate supplier account for goods and shipping. Square does not split a checkout payment or transfer it to Mouser, Printify or AliExpress automatically.</p>
        <p>Printify and enabled automatic Mouser products use verified paid-order fulfillment. Choose each product’s fulfillment mode and retail price in the product editor. AliExpress and Yuzu automatic integrations remain unconnected. Cost overruns use the shared product suspension controls in Orders.</p>
        <p class="help-copy">Mouser's Order API supports cards saved in your Mouser account. AliExpress exposes a payment-attempt option for an authorized DS account. A saved card alone is not proof that your application/account can use it successfully; ordering, authorization and payment must be tested together. Keep cards on the supplier's own billing page. Never enter card numbers, CVV, bank details or email passwords in this admin.</p>
        <p class="help-copy">Supplier-sourced drafts default to “Fulfillment pending” and cannot be purchased. For stock you actually receive and ship yourself, choose office fulfillment in its product editor and set stock/rates in Orders. Existing digital, office and Printify checkout continues through Square.</p>
        <p><a href="https://www.mouser.com/en/api-order/" target="_blank" rel="noopener noreferrer">Mouser ordering & saved cards ↗</a> · <a href="https://printify.com/app/" target="_blank" rel="noopener noreferrer">Printify billing ↗</a> · <a href="https://openservice.aliexpress.com/" target="_blank" rel="noopener noreferrer">AliExpress API console ↗</a></p>
      </section>
      </details>
      <details class="supplier-settings"><summary>Custom keycap fulfillment</summary><section class="admin-section"><h2>Custom keycap fulfillment</h2><p>Current designs are managed in Keycap profiles. Paid custom sets enter Orders with their private design JSON and delivery details. Download the packet, place the maker order manually and record its reference and tracking.</p></section></details>
    </fieldset>
  </div>
</template>
<style scoped>
.supplier-settings{margin:18px 0;border:1px solid var(--rule);padding:14px}.supplier-settings>summary{cursor:pointer;font-weight:700;padding:8px}.supplier-settings .admin-section{margin-bottom:0}
.supplier-callback{display:block;overflow-wrap:anywhere;padding:12px;border:1px solid var(--rule);margin:12px 0}.supplier-manager ol{padding-left:24px}.supplier-manager li{margin:8px 0;line-height:1.65}
.supplier-manager fieldset{border:0;padding:0;min-width:0}.supplier-manager p{line-height:1.65}.supplier-manager a{text-decoration:underline}.supplier-block{border:1px solid var(--rule);padding:18px;margin:16px 0}.supplier-result{display:flex;gap:20px}.supplier-result>img{width:100px;height:100px;object-fit:contain;flex-shrink:0;background:white}.supplier-result>div{min-width:0;overflow-wrap:anywhere}.supplier-table{overflow:auto}.supplier-table table{width:100%;border-collapse:collapse}.supplier-table th,.supplier-table td{padding:14px;text-align:left;border-bottom:1px solid var(--rule)}@media(max-width:600px){.supplier-manager .form-grid{grid-template-columns:minmax(0,1fr)}.supplier-result{flex-direction:column}.supplier-block{padding:12px}}
</style>
