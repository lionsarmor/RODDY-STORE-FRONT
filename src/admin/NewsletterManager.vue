<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { SUPPORT_EMAIL } from '../forum-api.js';
import MediaEditor from './MediaEditor.vue';
import { commerceRequest } from './commerce-api';
import { uploadFile } from './api';
import { dataUrlToBase64 } from './image';
import { formatPrice } from '../stores/catalog';
const props = defineProps({endpoint: String, token: String, connected: Boolean, github: Object, library: Array, products: Array});
const overview = ref(null);
const subscribers = ref([]);
const page = ref(1);
const search = ref('');
const hasMore = ref(false);
const suppressEmail = ref('');
const postalAddress = ref('');
const edition = ref(null);
const draft = ref(null);
const baseline = ref('');
const preview = ref(null);
const prepared = ref(null);
const busy = ref(false);
const mediaBusy = ref(0);
const error = ref('');
const message = ref('');
const featureId = ref('');
const dirty = computed(() => draft.value && JSON.stringify(draft.value) !== baseline.value);
const editable = computed(() => !edition.value?.sentAt);
const liveProducts = computed(() => (props.products || []).filter(p => p.active));
const api = (path, body) => commerceRequest(props.endpoint, '/admin/newsletters' + path, props.token, body);
function beforeUnload(event) { if (dirty.value) { event.preventDefault(); event.returnValue = ''; } }
window.addEventListener('beforeunload', beforeUnload);
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload));
watch(draft, () => { preview.value = null; prepared.value = null; }, {deep: true});
watch(() => [props.connected, props.token, props.endpoint], async () => {
  overview.value = null; subscribers.value = []; prepared.value = null;
  if (props.connected) await act(load);
  else { draft.value = null; edition.value = null; baseline.value = ''; preview.value = null; }
}, {immediate: true});
async function act(fn) {
  if (busy.value) return;
  busy.value = true; error.value = ''; message.value = '';
  try { await fn(); } catch (e) { error.value = e.message; }
  finally { busy.value = false; }
}
async function load() {
  overview.value = await api('');
  postalAddress.value = overview.value.settings.postalAddress;
  await list();
}
async function list() {
  const result = await api(`/subscribers?page=${page.value}&search=${encodeURIComponent(search.value)}`);
  subscribers.value = result.subscribers; hasMore.value = result.hasMore;
}
function blankBlock(kind) { return {kind, heading: '', body: '', image: '', alt: '', link: '', button: '', badge: '', price: ''}; }
function open(item) {
  edition.value = item;
  draft.value = JSON.parse(JSON.stringify(item.content));
  baseline.value = JSON.stringify(draft.value);
  preview.value = null; prepared.value = null;
}
function start() { open({content: {title: 'New RODDY newsletter', subject: 'A little news from RODDY', preheader: '', palette: 'confetti', blocks: [{...blankBlock('text'), heading: 'Hello from RODDY', body: 'Here is what we have been making.'}]}}); }
function duplicate() { edition.value = {content: draft.value}; draft.value.title += ' (copy)'; baseline.value = ''; }
function move(i, direction) { const to = i + direction; [draft.value.blocks[i], draft.value.blocks[to]] = [draft.value.blocks[to], draft.value.blocks[i]]; }
function feature() {
  const p = liveProducts.value.find(p => p.id === featureId.value); if (!p) return;
  const prices = p.merch?.variants.filter(v => v.enabled && v.available !== false).map(v => v.price) || [];
  const price = prices.length ? `From ${formatPrice(Math.min(...prices))}` : formatPrice(p.price);
  draft.value.blocks.push({...blankBlock('offer'), heading: p.name, body: (p.description || '').slice(0, 2000), image: p.coverImage || p.images?.[0] || p.image || '', alt: p.name, link: `https://roddy.world/#/product/${encodeURIComponent(p.id)}`, button: 'Take a look', badge: 'FROM THE RODDY SHOP', price});
}
async function save(asCopy = false) {
  for (const block of draft.value.blocks) {
    if (block.image?.startsWith('data:')) {
      const path = `img/newsletters/${crypto.randomUUID()}.jpg`;
      await uploadFile(props.github, 'public/' + path, dataUrlToBase64(block.image));
      block.image = `https://raw.githubusercontent.com/${encodeURIComponent(props.github.owner)}/${encodeURIComponent(props.github.repo)}/${encodeURIComponent(props.github.branch)}/public/${path}`;
    } else if (block.image && !block.image.startsWith('https://')) {
      if (!/^img\/[a-zA-Z0-9_./ -]+$/.test(block.image) || block.image.includes('..')) throw new Error('Use a public HTTPS picture or an image from your library.');
      block.image = `https://raw.githubusercontent.com/${encodeURIComponent(props.github.owner)}/${encodeURIComponent(props.github.repo)}/${encodeURIComponent(props.github.branch)}/public/${block.image}`;
      if (!block.image.startsWith('https://')) throw new Error('Use a public HTTPS image URL for email pictures.');
    }
  }
  const result = await api('/drafts', {content: draft.value, ...(!asCopy && edition.value?.id ? {id: edition.value.id, revision: edition.value.revision} : {})});
  open(result.campaign); overview.value = await api(''); message.value = 'Draft saved privately on the droplet. New pictures are public image assets.';
}
async function renderPreview() {
  if (draft.value.blocks.some(b => b.image?.startsWith('data:') || (b.image && !b.image.startsWith('https://')))) throw new Error('Save first to publish the pictures, then preview.');
  preview.value = await api('/preview', {content: draft.value});
}
async function prepare() {
  prepared.value = await api('/prepare', {id: edition.value.id, revision: edition.value.revision});
  preview.value = prepared.value;
  message.value = `Fresh recipient list prepared: ${prepared.value.count} active subscribers. This has not sent any emails.`;
}
async function copy(value) {
  try { await navigator.clipboard.writeText(value); message.value = 'Copied. Paste into the indicated field in your email composer.'; }
  catch { throw new Error('Clipboard unavailable. Select and copy the text shown below.'); }
}
async function copyRich() {
  if (!window.ClipboardItem || !navigator.clipboard?.write) throw new Error('Rich copy is unavailable here. Open the HTML download, select its contents and copy, or use plain text.');
  await navigator.clipboard.write([new ClipboardItem({'text/html': new Blob([prepared.value.html], {type: 'text/html'}), 'text/plain': new Blob([prepared.value.text], {type: 'text/plain'})})]);
  message.value = 'Newsletter copied with formatting. Paste into the email body, then inspect pictures, links and footer. Send yourself a test first.';
}
function download(value, name, type) {
  const url = URL.createObjectURL(new Blob([value], {type})); const a = document.createElement('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function exportCsv() {
  const res = await fetch(props.endpoint.replace(/\/$/, '') + '/admin/newsletters/subscribers.csv', {headers: {authorization: `Bearer ${props.token}`}});
  if (!res.ok) throw new Error('Subscriber export failed. Sign in and try again.');
  download(await res.text(), 'RODDY-newsletter-subscribers.csv', 'text/csv');
}
async function unsubscribe(email) { await api('/subscribers/unsubscribe', {email}); prepared.value = null; suppressEmail.value = ''; await load(); message.value = 'Address suppressed. It will be excluded from future BCC lists; public signup cannot reactivate it.'; }
async function record() {
  await api('/record-sent', {id: edition.value.id, revision: prepared.value.revision, audienceHash: prepared.value.audienceHash, confirmedManualSend: true});
  const id = edition.value.id; await load(); open(overview.value.campaigns.find(c => c.id === id)); message.value = 'Recorded as manually sent. This records your action; it does not verify delivery.';
}
</script>
<template>
  <div class="newsletter-admin">
    <section class="admin-section">
      <p class="eyebrow">YOUR OWN EMAIL ACCOUNT · NO DELIVERY SERVICE REQUIRED</p>
      <h2>Newsletters & advertisements</h2>
      <p>Create an edition here, then send it yourself with Proton Mail or Gmail. Subscribers and drafts are stored privately on your droplet. This page never sends email automatically.</p>
      <p v-if="!connected" class="notice">Connect to GitHub above to manage private newsletter data.</p>
      <button class="button small" :disabled="!connected || busy" @click="act(load)">Refresh saved editions & subscribers</button>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <p v-if="message" class="notice" role="status">{{ message }}</p>
    </section>
    <fieldset v-if="overview && connected" :disabled="busy || mediaBusy > 0">
      <section class="admin-section newsletter-instructions">
        <h2>How to send without sharing everyone's address</h2>
        <ol>
          <li><strong>Handle unsubscribe requests first.</strong> Check your inbox for “unsubscribe” replies and use the suppression control below before preparing any recipients.</li>
          <li><strong>Save the edition and refresh recipients immediately before sending.</strong> Copy one batch into <strong>BCC</strong>. Put <strong>{{ SUPPORT_EMAIL }} in To</strong>. Never paste the list into To or CC. This keeps customers' addresses private.</li>
          <li><strong>Copy the subject, then copy the formatted newsletter into the body.</strong> Check pictures, links, prices and the postal address. Email yourself a test first. Rich formatting can vary between email apps.</li>
          <li><strong>Send each batch once.</strong> Batches contain up to 50 subscribers, plus you in To. Check your account's current limits and wait if it limits sending. These are batches, not an unlimited sending allowance.</li>
          <li><strong>Record the edition only after every batch has been sent.</strong> The site cannot see your mailbox, detect delivery, or process replies automatically. Avoid sending an old export again.</li>
        </ol>
        <p><a href="https://proton.me/support/contact-groups" target="_blank" rel="noopener noreferrer">Proton recipient limits ↗</a> · <a href="https://support.google.com/mail/answer/22839" target="_blank" rel="noopener noreferrer">Gmail sending limits ↗</a></p>
      </section>
      <section class="admin-section">
        <h2>Newsletter footer</h2>
        <label>Public business mailing address or PO box<textarea v-model="postalAddress" rows="3" maxlength="500" placeholder="Business name, street or registered mailbox, city, state, postal code, country" /></label>
        <p class="help-copy">This address appears in every exported newsletter. Advertising emails need a valid postal address. If you do not want to use your home address, a registered PO box or commercial mailbox can work. You can collect opt-ins and save drafts now; sending exports unlock once you add your address.</p>
        <button class="button small" @click="act(async () => { await api('/settings', {postalAddress}); prepared = null; await load(); message = 'Footer saved.'; })">Save footer</button>
        <p class="help-copy">Every email includes “reply with unsubscribe” and an email link to {{ SUPPORT_EMAIL }}. Handle these requests here before the next mailing. <a href="https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business" target="_blank" rel="noopener noreferrer">FTC guidance ↗</a></p>
      </section>
      <section class="admin-section">
        <h2>Subscribers</h2>
        <p>{{ overview.counts.active || 0 }} active · {{ overview.counts.unsubscribed || 0 }} unsubscribed</p>
        <p class="help-copy">Only explicit website newsletter signups join this list. Purchasers and forum members are not added automatically. Protect downloaded recipient files; never put them in GitHub or share them publicly.</p>
        <div class="admin-actions"><label>Unsubscribe an email<input v-model="suppressEmail" type="email" placeholder="Address from the request" /></label><button class="button small" :disabled="!suppressEmail" @click="act(() => unsubscribe(suppressEmail))">Suppress this address</button><button class="button small" @click="act(exportCsv)">Download private CSV backup</button></div>
        <p class="help-copy">The CSV contains all records, including unsubscribed addresses for backup. Use the fresh BCC batches below for sending; do not send from the full CSV. A suppressed address stays suppressed even if someone submits it again.</p>
        <div class="admin-actions"><label>Find subscriber<input v-model="search" maxlength="254" @keydown.enter.prevent="act(async () => { page = 1; await list(); })" /></label><button class="button small" @click="act(async () => { page = 1; await list(); })">Search</button></div>
        <div class="newsletter-table"><table><thead><tr><th>Email</th><th>Status</th><th>Action</th></tr></thead><tbody><tr v-for="subscriber in subscribers" :key="subscriber.id"><td>{{ subscriber.email }}</td><td>{{ subscriber.status }}</td><td><button v-if="subscriber.status === 'active'" class="button small" @click="act(() => unsubscribe(subscriber.email))">Unsubscribe</button></td></tr></tbody></table></div>
        <p v-if="!subscribers.length">No matching subscriber records.</p>
        <div class="admin-actions"><button class="button small" :disabled="page === 1" @click="act(async () => { page--; await list(); })">Previous</button><span>Page {{ page }}</span><button class="button small" :disabled="!hasMore" @click="act(async () => { page++; await list(); })">Next</button></div>
      </section>
      <section class="admin-section">
        <h2>Saved editions</h2>
        <p class="help-copy">Save before switching editions. If another browser updates a draft, your edits are preserved and you can save a new copy. The most recent 100 editions appear here.</p>
        <button class="button primary" :disabled="dirty" @click="start">New newsletter</button>
        <div class="edition-list"><button v-for="item in overview.campaigns" :key="item.id" class="button small" :disabled="dirty" @click="open(item)">{{ item.content.title }} · {{ item.sentAt ? `Manually sent (${item.sentCount})` : 'Draft' }}</button></div>
      </section>
      <section v-if="draft" class="admin-section">
        <h2>{{ edition?.sentAt ? 'Sent edition (read only)' : 'Build your newsletter' }}</h2>
        <p v-if="dirty" class="notice">Unsaved edits. Save this draft or save a new copy before switching editions.</p>
        <fieldset :disabled="!editable">
          <div class="form-grid"><label>Private draft name<input v-model="draft.title" maxlength="120" /></label><label>Email subject<input v-model="draft.subject" maxlength="150" /></label><label>Inbox preview text<input v-model="draft.preheader" maxlength="180" /></label><label>Colors<select v-model="draft.palette"><option value="confetti">Confetti</option><option value="cyan">Ocean</option><option value="rose">Rose</option><option value="amber">Amber</option></select></label></div>
          <section v-for="(block, i) in draft.blocks" :key="i" class="newsletter-block">
            <div class="admin-actions"><h3>{{ i + 1 }} · {{ block.kind }}</h3><button class="button small" :disabled="i === 0" :aria-label="`Move section ${i+1} earlier`" @click="move(i, -1)">↑</button><button class="button small" :disabled="i === draft.blocks.length - 1" :aria-label="`Move section ${i+1} later`" @click="move(i, 1)">↓</button><button class="button small" :disabled="draft.blocks.length === 1" @click="draft.blocks.splice(i, 1)">Remove section</button></div>
            <template v-if="block.kind !== 'divider'">
              <label>Heading<input v-model="block.heading" maxlength="120" /></label><label>Text<textarea v-model="block.body" rows="5" maxlength="2000" /></label>
              <MediaEditor :model-value="block.image ? [block.image] : []" single :library="library" title="Newsletter picture" @update:model-value="block.image = $event[0] || ''" @busy="mediaBusy = Math.max(0, mediaBusy + ($event ? 1 : -1))" />
              <label>Picture description (for readers who cannot see the image)<input v-model="block.alt" maxlength="180" /></label>
              <div class="form-grid"><label>Button destination (HTTPS)<input v-model="block.link" type="url" maxlength="1000" /></label><label>Button label<input v-model="block.button" maxlength="60" /></label><label v-if="block.kind === 'offer'">Offer badge<input v-model="block.badge" maxlength="50" placeholder="NEW / SALE / THIS WEEK" /></label><label v-if="block.kind === 'offer'">Price / offer line<input v-model="block.price" maxlength="80" /></label></div>
            </template>
          </section>
          <div class="admin-actions"><button v-for="kind in ['text', 'image', 'offer', 'divider']" :key="kind" class="button small" :disabled="draft.blocks.length >= 12" @click="draft.blocks.push(blankBlock(kind))">Add {{ kind === 'image' ? 'picture' : kind }}</button></div>
          <div class="admin-actions"><label>Feature a storefront product<select v-model="featureId"><option value="">Choose product…</option><option v-for="p in liveProducts" :key="p.id" :value="p.id">{{ p.name }}</option></select></label><button class="button small" :disabled="!featureId || draft.blocks.length >= 12" @click="feature">Add product offer</button></div>
        </fieldset>
        <p class="help-copy">Promotional copy does not change store prices. Check that advertised prices and availability match your store. Saving uploads new pictures to your public GitHub image library; draft text and subscriber data remain private. Use ordinary text; HTML code is escaped.</p>
        <div class="admin-actions"><button class="button primary" :disabled="!editable" @click="act(() => save())">Save draft & pictures</button><button class="button small" @click="act(() => save(true))">Save as new copy</button><button class="button small" @click="act(renderPreview)">Preview</button><button v-if="dirty" class="button small" @click="draft = null; edition = null; baseline = ''; preview = null; prepared = null">Discard unsaved edits</button><button v-if="edition?.sentAt" class="button small" @click="duplicate">Duplicate to edit</button></div>
        <p class="help-copy">Newsletter drafts save independently of the catalog's Publish button above.</p>
        <iframe v-if="preview" title="Newsletter preview" sandbox="" :srcdoc="preview.html" class="newsletter-preview" />
      </section>
      <section v-if="draft && edition?.id && !edition?.sentAt" class="admin-section">
        <h2>Prepare for Proton Mail or Gmail</h2>
        <p class="help-copy">Save edits first. Process unsubscribe requests, then refresh recipients before every mailing. Nothing here sends email or opens a bulk email composer automatically.</p>
        <button class="button primary" :disabled="dirty || !overview.settings.postalAddress" @click="act(prepare)">Refresh recipients & prepare email</button>
        <p v-if="!overview.settings.postalAddress" class="notice">Add your postal address in Newsletter footer to unlock sending exports. You can preview and save drafts now.</p>
        <template v-if="prepared">
          <p class="notice">{{ prepared.count }} active subscribers · {{ prepared.batches.length }} batches. Put yourself in To and paste recipients only into BCC. Review and send each batch once in your email account.</p>
          <label>To (your address)<input readonly :value="SUPPORT_EMAIL" /></label><button class="button small" @click="act(() => copy(SUPPORT_EMAIL))">Copy To</button>
          <label>Subject<input readonly :value="prepared.subject" /></label><button class="button small" @click="act(() => copy(prepared.subject))">Copy subject</button>
          <div v-for="(batch, i) in prepared.batches" :key="i" class="newsletter-block"><label>BCC batch {{ i + 1 }} / {{ prepared.batches.length }}<textarea readonly rows="4" :value="batch" /></label><button class="button small" @click="act(() => copy(batch))">Copy BCC batch {{ i + 1 }}</button></div>
          <p v-if="!prepared.count">No active subscribers yet. You can still copy the content and send yourself a test.</p>
          <div class="admin-actions"><button class="button primary" @click="act(copyRich)">Copy formatted email body</button><button class="button small" @click="act(() => copy(prepared.text))">Copy plain-text body</button><button class="button small" @click="download(prepared.html, 'RODDY-newsletter.html', 'text/html')">Download email HTML</button></div>
          <p class="help-copy">If formatted copy is unavailable, open the downloaded HTML in your browser, select and copy the newsletter, then paste it into your email body. Do not paste raw HTML code into the composer. If pictures or formatting disappear, use the plain-text version. Test in your own inbox first.</p>
          <label>Plain-text fallback<textarea readonly rows="10" :value="prepared.text" /></label>
          <button class="button small" :disabled="!prepared.count" @click="act(record)">I sent every batch — record as manually sent</button>
          <p class="help-copy">This is your own record, not proof of delivery. The site cannot tell whether a batch was sent. Keep track of batches in your email account to avoid duplicates.</p>
        </template>
      </section>
    </fieldset>
  </div>
</template>
<style scoped>
.newsletter-admin fieldset{border:0;padding:0;min-width:0}.newsletter-admin label{display:grid;gap:6px;margin:12px 0}.newsletter-admin textarea{width:100%;min-width:0;resize:vertical;line-height:1.5;overflow-wrap:anywhere}.newsletter-admin p,.newsletter-admin li{line-height:1.65}.newsletter-instructions{color:#182023;background:#fff6df;border-top:6px solid #d96987}.newsletter-instructions ol{padding-left:24px;list-style:decimal}.newsletter-instructions li{margin:12px 0}.newsletter-admin a{text-decoration:underline}.newsletter-block{padding:18px;border:1px solid var(--admin-border,#d1c9bc);border-radius:10px;margin:18px 0}.newsletter-preview{width:100%;height:650px;margin-top:20px;border:1px solid #bbb;border-radius:10px;background:#efede7}.edition-list{display:flex;flex-wrap:wrap;gap:10px;margin-top:15px}.newsletter-table{max-width:100%;overflow:auto}.newsletter-table table{width:100%;border-collapse:collapse}.newsletter-table th,.newsletter-table td{text-align:left;padding:12px;border-bottom:1px solid #ddd;overflow-wrap:anywhere}.newsletter-admin .admin-actions{align-items:center}.newsletter-admin .form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}@media(max-width:700px){.newsletter-admin .form-grid{grid-template-columns:1fr}.newsletter-preview{height:500px}.newsletter-block{padding:12px}.newsletter-admin .admin-actions{flex-wrap:wrap}}
</style>
