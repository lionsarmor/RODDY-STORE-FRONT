<script setup>
import {
  computed,
  onMounted,
  onBeforeUnmount,
  reactive,
  ref,
  watch,
} from "vue";
import RoddyLogo from "../components/RoddyLogo.vue";
import ProductTags from "../components/ProductTags.vue";
import ThemeOverlay from "../components/ThemeOverlay.vue";
import OrderManager from "./OrderManager.vue";
import CustomerManager from "./CustomerManager.vue";
import SupplierManager from "./SupplierManager.vue";
import NewsletterManager from "./NewsletterManager.vue";
import ForumManager from "./ForumManager.vue";
import MerchEditor from "./MerchEditor.vue";
import { importPrintifyProduct, priceLabel } from "../merch.js";
import SaleNotifications from './SaleNotifications.vue';
import KeycapManager from './KeycapManager.vue';
import PcbWizard from './PcbWizard.vue';
import ProjectWorkshop from './ProjectWorkshop.vue';
import CategoryManager from './CategoryManager.vue';
import { categoryVisible } from '../category-visibility.js';
import ProductEditor from "./ProductEditor.vue";
import MediaEditor from "./MediaEditor.vue";
import { useThemeStore } from "../stores/theme";
import { useUiStore } from "../stores/ui";
import {
  normalizeCatalog,
  normalizeProduct,
  validateCatalog,
} from "../catalog-model.js";
import { productImageUrl, formatPrice } from "../stores/catalog";
import { fetchCatalog, fetchCatalogRevision, saveCatalog, uploadFile, listRepoImages } from "./api";
import { mergeCatalog } from "./catalog-merge.js";
import { commerceRequest } from "./commerce-api";
import { blankProduct, slugify } from "./utils";
import { dataUrlToBase64 } from "./image";
import "./admin.css";

useThemeStore();
const ui = useUiStore();
const CONFIG_KEY = "roddy:admin:config";
const tab = ref(window.location.hash === "#workshop" ? "workshop" : "overview");
watch(tab, value => { window.history.replaceState(null, "", value === "workshop" ? "#workshop" : window.location.pathname + window.location.search); });
const tabs = [
  { id: "overview", label: "Overview", icon: "◫" },
  { id: "products", label: "Products", icon: "▦" },
  { id: "categories", label: "Categories", icon: "⌘" },
  { id: "tags", label: "Tags & colors", icon: "◉" },
  { id: "homepage", label: "Homepage", icon: "↗" },
  { id: "checkout", label: "Checkout & Square", icon: "▣" },
  { id: "suppliers", label: "Suppliers & imports", icon: "⇄" },
  { id: "printify", label: "Printify merchandise", icon: "◇" },
  { id: "keycaps", label: "Keycap profiles", icon: "⌨" },
  { id: "orders", label: "Orders", icon: "▤" },
  { id: "customers", label: "Customers", icon: "☺" },
  { id: "workshop", label: "Project Workshop", icon: "▧" },
  { id: "pcb", label: "Electronics / PCBWay", icon: "⚡" },
  { id: "newsletters", label: "Newsletters & ads", icon: "✉" },
  { id: "forum", label: "Community forum", icon: "☷" },
];
const form = reactive({
  owner: "lionsarmor",
  repo: "RODDY-STORE-FRONT",
  branch: "main",
  token: "",
  remember: false,
});
const connected = ref(false);
const ordersRefresh = ref(0);
const orderInbox = ref(0);
const showConnection = ref(false);
const catalog = ref(null);
const sha = ref(null);
const baseline = ref("");
const mergeReview = ref(null);
const saving = ref(false);
const pendingMedia = ref(0);
const status = ref("");
const error = ref("");
const library = ref([]);
const selected = ref(null);
const search = ref("");
const categoryFilter = ref("");
const stateFilter = ref("");
const draftAvailable = ref(false);
const draftMessage = ref("");
const commerceBusy = ref(false);
const connectionStatus = ref(null);
const printifyStatus = ref(null);
const printifyMapping = reactive({});
const livePrintifyProducts = reactive({});
const draftKey = computed(
  () => `roddy:admin:draft:${form.owner}/${form.repo}@${form.branch}`,
);
const dirty = computed(
  () => catalog.value && JSON.stringify(catalog.value) !== baseline.value,
);
const issues = computed(() =>
  catalog.value ? validateCatalog(catalog.value) : [],
);
const filtered = computed(() =>
  (catalog.value?.products || []).filter(
    (p) =>
      `${p.name} ${p.sku} ${p.id}`
        .toLowerCase()
        .includes(search.value.toLowerCase()) &&
      (!categoryFilter.value || p.category === categoryFilter.value) &&
      (!stateFilter.value ||
        (stateFilter.value === "hidden"
          ? !p.active || !categoryVisible(catalog.value.categories.find(c => c.id === p.category))
          : p.active && p.status === stateFilter.value)),
  ),
);
const currentTab = computed(() => tabs.find((t) => t.id === tab.value));
const heroImages = computed({
  get: () =>
    catalog.value?.settings.heroImage ? [catalog.value.settings.heroImage] : [],
  set: (value) => {
    catalog.value.settings.heroImage = value[0] || "";
  },
});
const stats = computed(() => [
  {
    label: "Products",
    value: catalog.value?.products.length || 0,
    tab: "products",
  },
  {
    label: "Live in catalog",
    value: catalog.value?.products.filter((p) => p.active && categoryVisible(catalog.value.categories.find(c => c.id === p.category))).length || 0,
    tab: "products",
  },
  {
    label: "Coming soon",
    value:
      catalog.value?.products.filter((p) => p.status === "coming-soon")
        .length || 0,
    tab: "products",
  },
  {
    label: "Categories",
    value: catalog.value?.categories.length || 0,
    tab: "categories",
  },
]);
let draftTimer;
function installCatalog(data, nextSha = null) {
  mergeReview.value = null;
  catalog.value = normalizeCatalog(data);
  sha.value = nextSha;
  baseline.value = JSON.stringify(catalog.value);
  selected.value = null;
}
onMounted(async () => {
  try {
    const saved = JSON.parse(localStorage.getItem(CONFIG_KEY) || "null");
    if (saved) Object.assign(form, saved, { remember: !!saved.token });
    const res = await fetch("./data/products.json", { cache: "no-store" });
    if (!res.ok) throw new Error("Could not load the catalog.");
    installCatalog(await res.json());
    draftAvailable.value = !!localStorage.getItem(draftKey.value);
  } catch (e) {
    error.value = e.message;
  }
});
watch(
  catalog,
  () => {
    clearTimeout(draftTimer);
    if (!dirty.value) return;
    draftTimer = setTimeout(() => {
      try {
        localStorage.setItem(
          draftKey.value,
          JSON.stringify({
            catalog: catalog.value,
            sha: sha.value,
            baseline: baseline.value ? JSON.parse(baseline.value) : null,
            savedAt: new Date().toISOString(),
          }),
        );
        draftMessage.value = "Draft saved on this device";
      } catch {
        draftMessage.value =
          "Browser storage is full. Export a backup to preserve your images and edits.";
      }
    }, 500);
  },
  { deep: true },
);
function beforeUnload(event) {
  if (dirty.value) {
    event.preventDefault();
    event.returnValue = "";
  }
}
window.addEventListener("beforeunload", beforeUnload);
onBeforeUnmount(() => {
  clearTimeout(draftTimer);
  window.removeEventListener("beforeunload", beforeUnload);
});
async function connect() {
  if (!form.owner || !form.repo || !form.token) {
    error.value = "Owner, repository and GitHub token are required.";
    return;
  }
  const keepDraft = dirty.value;
  saving.value = true;
  error.value = "";
  status.value = "Connecting to GitHub…";
  try {
    const result = await fetchCatalog(form);
    if (keepDraft) reconcileCatalog(result);
    else installCatalog(result.catalog, result.sha);
    connected.value = true;
    showConnection.value = false;
    if (!keepDraft) status.value = "Connected. You can publish changes to GitHub.";
    if (form.remember) localStorage.setItem(CONFIG_KEY, JSON.stringify(form));
    else localStorage.removeItem(CONFIG_KEY);
    draftAvailable.value = !!localStorage.getItem(draftKey.value);
    try {
      library.value = await listRepoImages(form);
    } catch (e) {
      status.value += " Image library could not load: " + e.message;
    }
  } catch (e) {
    error.value = e.message;
    status.value = "";
  } finally {
    saving.value = false;
  }
}
function disconnect() {
  connected.value = false;
  form.token = "";
  localStorage.removeItem(CONFIG_KEY);
  status.value = "Disconnected. Your catalog draft is still open.";
  connectionStatus.value = null;
  printifyStatus.value = null;
}
function reconcileCatalog(result, base = JSON.parse(baseline.value), local = catalog.value) {
  const remote = normalizeCatalog(result.catalog);
  const merged = mergeCatalog(base, local, remote);
  if (merged.conflicts.length) {
    mergeReview.value = {
      base, local: JSON.parse(JSON.stringify(local)), remote,
      sha: result.sha, conflicts: merged.conflicts, choices: {},
    };
    status.value = "Some fields changed in both versions. Choose which values to keep below. Your draft is intact.";
    return false;
  }
  applyMergedCatalog(merged.catalog, remote, result.sha);
  status.value = "Latest GitHub changes combined with your edits. Review, then publish.";
  return true;
}
function applyMergedCatalog(merged, remote, nextSha) {
  const selectedId = selected.value?.id;
  catalog.value = merged;
  baseline.value = JSON.stringify(remote);
  sha.value = nextSha;
  selected.value = catalog.value.products.find((p) => p.id === selectedId) || null;
  mergeReview.value = null;
}
function resolveMerge() {
  const review = mergeReview.value;
  const merged = mergeCatalog(review.base, review.local, review.remote, review.choices);
  if (merged.conflicts.length) return;
  applyMergedCatalog(merged.catalog, review.remote, review.sha);
  draftAvailable.value = false;
  error.value = "";
  status.value = "Choices applied to your draft. Review, then publish.";
}
function conflictValue(value) {
  if (value === undefined) return "Deleted";
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > 180 ? text.slice(0, 180) + "…" : text;
}
async function refreshCatalog() {
  saving.value = true;
  error.value = "";
  try {
    const result = await fetchCatalog(form);
    if (dirty.value) reconcileCatalog(result);
    else {
      installCatalog(result.catalog, result.sha);
      status.value = "Reloaded the latest published catalog.";
    }
  } catch (e) {
    error.value = e.message;
  } finally {
    saving.value = false;
  }
}
async function restoreDraft() {
  saving.value = true;
  error.value = "";
  try {
    const draft = JSON.parse(localStorage.getItem(draftKey.value));
    if (!draft?.catalog) throw new Error("No saved draft found.");
    if (dirty.value && !confirm("Replace the currently open edits with your saved draft? Export JSON first to keep both.")) return;
    if (!draft.baseline && !connected.value) throw new Error("Connect to GitHub first to recover this older draft safely. Your saved draft is intact.");
    const base = normalizeCatalog(draft.baseline || await fetchCatalogRevision(form, draft.sha));
    if (connected.value) {
      const result = await fetchCatalog(form);
      if (reconcileCatalog(result, base, normalizeCatalog(draft.catalog))) draftAvailable.value = false;
    } else {
      catalog.value = normalizeCatalog(draft.catalog);
      baseline.value = JSON.stringify(base);
      sha.value = draft.sha;
      selected.value = null;
      draftAvailable.value = false;
      status.value = "Draft restored. Connect to GitHub to combine it with the latest catalog.";
    }
  } catch (e) {
    error.value = e.message;
  } finally {
    saving.value = false;
  }
}
function discard() {
  if (!confirm("Discard all edits since this catalog was loaded or published?"))
    return;
  clearTimeout(draftTimer);
  mergeReview.value = null;
  catalog.value = JSON.parse(baseline.value);
  selected.value = null;
  localStorage.removeItem(draftKey.value);
  draftAvailable.value = false;
  draftMessage.value = "";
  status.value = "Draft discarded.";
}
async function publish() {
  if (mergeReview.value) {
    error.value = "Choose which conflicting values to keep before publishing.";
    return;
  }
  if (pendingMedia.value) {
    error.value = "Wait for the images to finish preparing before publishing.";
    return;
  }
  error.value = "";
  if (issues.value.length) {
    error.value = issues.value.join(" ");
    return;
  }
  if (!connected.value) {
    showConnection.value = true;
    return;
  }
  saving.value = true;
  status.value = "Preparing publication…";
  try {
    // Compare with the latest catalog before uploading any media or writing.
    const latest = await fetchCatalog(form);
    if (!reconcileCatalog(latest)) return;
    if (issues.value.length) throw new Error(issues.value.join(" "));
    const snapshot = JSON.parse(JSON.stringify(catalog.value));
    if (
      /(?:sk_(?:live|test)_|github_pat_|ghp_)[a-zA-Z0-9_]{10,}/.test(
        JSON.stringify(snapshot),
      )
    )
      throw new Error(
        "A secret token was found in the catalog. Remove it from public fields before publishing.",
      );
    const copiedImages=new Map();
    for (const p of snapshot.products) for (const v of p.merch?.variants || []) {
      if (/^https:\/\/images-api\.printify\.com\//.test(v.image || '')) {
        if(!copiedImages.has(v.image)){const data=await commerceRequest(snapshot.settings.checkoutEndpoint,'/admin/catalog-images',form.token,{url:v.image});copiedImages.set(v.image,data.image);}
        v.image=copiedImages.get(v.image);
      }
    }
    const sources = new Set();
    for (const p of snapshot.products)
      [p.coverImage, ...p.images].forEach((src) => {
        if (src?.startsWith("data:")) sources.add(src);
      });
    for(const p of snapshot.products)for(const v of p.merch?.variants || [])if(v.image?.startsWith("data:"))sources.add(v.image);
    if (snapshot.settings.heroImage?.startsWith("data:"))
      sources.add(snapshot.settings.heroImage);
    const uploaded = new Map();
    let index = 0;
    for (const src of sources) {
      status.value = `Uploading image ${++index} of ${sources.size}…`;
      const path = `img/products/roddy-${crypto.randomUUID()}.jpg`;
      await uploadFile(form, "public/" + path, dataUrlToBase64(src));
      uploaded.set(src, path);
    }
    for (const p of snapshot.products) {
      p.coverImage = uploaded.get(p.coverImage) || p.coverImage;
      p.images = p.images.map((src) => uploaded.get(src) || src);
      for(const v of p.merch?.variants || [])v.image=uploaded.get(v.image) || v.image;
    }
    snapshot.settings.heroImage =
      uploaded.get(snapshot.settings.heroImage) || snapshot.settings.heroImage;
    const nextSha = await saveCatalog({ ...form, sha: sha.value }, snapshot);
    installCatalog(snapshot, nextSha);
    clearTimeout(draftTimer);
    localStorage.removeItem(draftKey.value);
    draftAvailable.value = false;
    draftMessage.value = "";
    status.value =
      "Published. The storefront will pick up your changes shortly.";
  } catch (e) {
    error.value = e.message;
    status.value = "Publication did not complete. Your draft is intact.";
  } finally {
    saving.value = false;
  }
}
function addProduct() {
  const p = normalizeProduct(
    blankProduct(new Set(catalog.value.products.map((p) => p.id))),
  );
  p.category = catalog.value.categories[0]?.id || "";
  p.pricePending = true;
  catalog.value.products.unshift(p);
  selected.value = p;
  tab.value = "products";
}
function duplicate() {
  const p = JSON.parse(JSON.stringify(selected.value));
  const base = p.id + "-copy";
  p.id = uniqueId(base, catalog.value.products);
  p.name += " (copy)";
  p.active = false;
  p.featured = false;
  p.sku += "-COPY";
  catalog.value.products.unshift(p);
  selected.value = p;
}
function removeProduct() {
  if (!confirm(`Delete ${selected.value.name} from this draft?`)) return;
  const id = selected.value.id;
  catalog.value.products = catalog.value.products.filter(
    (p) => p !== selected.value,
  );
  if (catalog.value.settings.heroProductId === id)
    catalog.value.settings.heroProductId = "";
  selected.value = null;
}
function uniqueId(base, list) {
  let id = base;
  let i = 2;
  while (list.some((x) => x.id === id)) id = base + "-" + i++;
  return id;
}
function move(list, i, direction) {
  const target = i + direction;
  if (target >= 0 && target < list.length)
    [list[i], list[target]] = [list[target], list[i]];
}
function addTag() {
  catalog.value.tags.push({
    id: uniqueId("new-tag", catalog.value.tags),
    label: "New tag",
    color: "#dac6ff",
  });
}
function removeTag(t) {
  catalog.value.products.forEach((p) => {
    p.tags = p.tags.filter((id) => id !== t.id);
  });
  catalog.value.tags = catalog.value.tags.filter((tag) => tag !== t);
}
function exportCatalog() {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(mergeReview.value?.local || catalog.value, null, 2)], {
      type: "application/json",
    }),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "roddy-catalog-backup.json";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function importCatalog(event) {
  const file = event.target.files[0];
  event.target.value = "";
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    if (!Array.isArray(data.products) || !Array.isArray(data.categories))
      throw new Error("Choose a RODDY catalog JSON backup.");
    const normalized = normalizeCatalog(data);
    const errors = validateCatalog(normalized);
    if (errors.length) throw new Error(errors.join(" "));
    if (dirty.value && !confirm("Replace your current draft with this backup?"))
      return;
    catalog.value = normalized;
    selected.value = null;
    status.value = "Backup imported into draft. Review before publishing.";
  } catch (e) {
    error.value = e.message;
  }
}
function preview() {
  try {
    sessionStorage.setItem("roddy:preview", JSON.stringify(catalog.value));
    window.open("./index.html?preview=1#/", "_blank");
  } catch {
    error.value =
      "Preview storage is full. Export a backup, then reduce the number or size of draft images.";
  }
}
async function commerce(action) {
  commerceBusy.value = true;
  error.value = "";
  try {
    await action();
  } catch (e) {
    error.value = e.message;
  } finally {
    commerceBusy.value = false;
  }
}
function checkConnection() {
  commerce(async () => {
    connectionStatus.value = await commerceRequest(
      catalog.value.settings.checkoutEndpoint,
      "/health",
    );
  });
}
function loadPrintify(page = 1) {
  commerce(async () => {
    printifyStatus.value = await commerceRequest(
      catalog.value.settings.checkoutEndpoint, `/admin/printify?page=${page}`, form.token,
    );
    for (const product of printifyStatus.value.products) {
      printifyMapping[product.id] ||= catalog.value.products.find(p => p.merch?.productId === product.id)?.id || "";
    }
  });
}
function syncPrintify(source, targetId) {
  commerce(async () => {
    const target = catalog.value.products.find(p => p.id === targetId);
    if (!target || target.type !== "physical") throw new Error("Choose a physical storefront product first.");
    const detail = await commerceRequest(catalog.value.settings.checkoutEndpoint, `/admin/printify/products/${encodeURIComponent(source.id)}`, form.token);
    livePrintifyProducts[targetId] = detail.product;
    Object.assign(target, importPrintifyProduct(target, detail.product, detail.shopId));
    status.value = `Imported ${target.merch.variants.length} combinations for ${target.name}. Review prices and shipping, then publish your draft.`;
  });
}

</script>
<template>
  <div class="admin-app">
    <header class="admin-header">
      <a href="./index.html"
        ><RoddyLogo kind="full_logo" class="h-8 w-auto" /></a
      ><span class="admin-wordmark"
        >CONTROL DESK <small>STORE OPERATIONS / V2</small></span
      >
      <div>
        <button class="button small" @click="ui.openThemeOverlay()">
          ◧ Theme</button
        ><a href="./index.html" target="_blank" class="button small"
          >View store ↗</a
        >
      </div>
    </header>
    <div class="admin-layout">
      <aside class="admin-sidebar">
        <p class="eyebrow">YOUR CORPORATION, AT A GLANCE</p>
        <nav aria-label="Admin sections">
          <button
            v-for="t in tabs"
            :key="t.id"
            :class="{ active: tab === t.id }"
            @click="
              tab = t.id;
              selected = null;
              error = '';
            "
          >
            <span>{{ t.icon }}</span
            >{{ t.label
            }}<span v-if="t.id === 'products'" class="nav-count">{{
              catalog?.products.length || 0
            }}</span><span v-if="t.id === 'orders' && connected && orderInbox" class="nav-count">{{orderInbox}}</span>
          </button>
        </nav>
        <div class="sidebar-bottom">
          <span class="eyebrow"
            ><span class="status-dot" />{{
              connected ? "GITHUB CONNECTED" : "LOCAL DRAFT MODE"
            }}</span
          >
          <p>{{ form.owner }}/{{ form.repo }}</p>
          <button class="text-button" @click="showConnection = !showConnection">
            {{ connected ? "Manage connection" : "Connect to publish" }} ↗
          </button>
        </div>
      </aside>
      <main class="admin-main">
        <div class="admin-page-heading">
          <div>
            <p class="eyebrow">RODDY / MISSION CONTROL</p>
            <h1>{{ currentTab.label }}</h1>
          </div>
          <div class="admin-actions">
            <span :class="dirty ? 'draft-dot' : 'saved-dot'">{{
              dirty ? "Unpublished changes" : "Draft up to date"
            }}</span
            ><button
              class="button small"
              :disabled="!catalog || saving"
              @click="preview"
            >
              Preview ↗</button
            ><button
              class="button primary small"
              :disabled="
                !catalog || saving || pendingMedia > 0 || issues.length > 0
              "
              @click="publish"
            >
              {{ saving ? "Working…" : "Publish changes ↑" }}
            </button>
          </div>
        </div>
        <p v-if="status" class="notice" role="status">{{ status }}</p>
        <p v-if="error" class="notice form-error" role="alert">{{ error }}</p>
        <div v-if="showConnection" class="admin-section connection-panel">
          <div class="field-heading">
            <h2>GitHub connection</h2>
            <button class="text-button" @click="showConnection = false">
              Close ×
            </button>
          </div>
          <p class="help-copy">
            Connect with a fine-grained token scoped to this repository, with
            Contents: Read and write.
          </p>
          <form @submit.prevent="connect">
            <div class="form-grid">
              <label
                >Owner<input
                  v-model="form.owner"
                  required
                  :disabled="connected" /></label
              ><label
                >Repository<input
                  v-model="form.repo"
                  required
                  :disabled="connected" /></label
              ><label
                >Branch<input
                  v-model="form.branch"
                  required
                  :disabled="connected" /></label
              ><label
                >GitHub token<input
                  v-model="form.token"
                  type="password"
                  autocomplete="off"
                  required
                  :disabled="connected"
              /></label>
            </div>
            <label class="check"
              ><input v-model="form.remember" type="checkbox" />Remember token
              on this device</label
            >
            <div class="admin-actions">
              <button
                v-if="!connected"
                class="button primary"
                :disabled="saving"
              >
                Connect & load catalog</button
              ><button v-else type="button" class="button" @click="disconnect">
                Disconnect
              </button>
            </div>
          </form>
        </div>
        <div v-if="draftAvailable" class="notice draft-recovery">
          There is a saved draft on this device.<button
            class="button small"
            :disabled="saving || !!mergeReview"
            @click="restoreDraft"
          >
            Restore draft</button
          ><button class="text-button" @click="draftAvailable = false">
            Dismiss
          </button>
        </div>
        <section v-if="mergeReview" class="notice merge-review" aria-label="Review conflicting edits">
          <h2>Choose which edits to keep</h2>
          <p>Other changes will be combined automatically. Nothing is published until you click Publish.</p>
          <div v-for="conflict in mergeReview.conflicts" :key="conflict.path" class="merge-field">
            <label>
              <strong>{{ conflict.path }}</strong>
              <select v-model="mergeReview.choices[conflict.path]" :aria-label="conflict.path">
                <option :value="undefined" disabled>Choose a version</option>
                <option value="local">Keep my edit</option>
                <option value="remote">Keep GitHub version</option>
              </select>
            </label>
            <p><b>My edit:</b> {{ conflictValue(conflict.local) }}</p>
            <p><b>GitHub:</b> {{ conflictValue(conflict.remote) }}</p>
          </div>
          <div class="admin-actions">
            <button class="button primary" :disabled="saving || mergeReview.conflicts.some(c => !mergeReview.choices[c.path])" @click="resolveMerge">Apply choices to draft</button>
            <button class="button" @click="exportCatalog">Export my draft ↓</button>
          </div>
        </section>
        <details v-if="issues.length" class="notice validation-list">
          <summary>
            {{ issues.length }} item(s) need attention before publishing
          </summary>
          <ul>
            <li v-for="issue in issues" :key="issue">{{ issue }}</li>
          </ul>
        </details>
        <SaleNotifications v-if="catalog" :visible="tab==='orders'" :endpoint="catalog.settings.checkoutEndpoint" :token="form.token" :connected="connected" @open-orders="tab='orders'" @new-sale="ordersRefresh++" @queue-update="orderInbox=$event" />
        <fieldset v-if="catalog" :disabled="saving || !!mergeReview" class="admin-workspace">
          <template v-if="tab === 'overview'">
            <div class="admin-welcome">
              <div>
                <p class="eyebrow">READY WHEN YOU ARE.</p>
                <h2>BIG IDEAS.<br />YOU'RE IN CONTROL.</h2>
                <p>
                  Your products, your storefront, your next release. All from
                  one desk.
                </p>
                <button class="button primary" @click="addProduct">
                  Add a product +
                </button>
              </div>
              <RoddyLogo
                kind="badge"
                class="admin-welcome-logo"
                aria-hidden="true"
              />
            </div>
            <div class="stat-grid">
              <button
                v-for="stat in stats"
                :key="stat.label"
                @click="tab = stat.tab"
              >
                <small>{{ stat.label }}</small
                ><strong>{{ stat.value.toString().padStart(2, "0") }}</strong
                ><span>↗</span>
              </button>
            </div>
            <div class="admin-two-col">
              <section class="admin-section">
                <p class="eyebrow">STORE READINESS</p>
                <h2>Before you open the doors</h2>
                <div class="readiness-row">
                  <span>Products & departments</span
                  ><b>{{
                    catalog.products.length ? "Ready" : "Add products"
                  }}</b>
                </div>
                <div class="readiness-row">
                  <span>GitHub publishing</span
                  ><b>{{ connected ? "Connected" : "Connect GitHub" }}</b>
                </div>
                <div class="readiness-row">
                  <span>Square checkout</span
                  ><b>{{
                    catalog.settings.checkoutEnabled
                      ? "Enabled in settings"
                      : "Setup needed"
                  }}</b>
                </div>
                <div class="readiness-row">
                  <span>Catalog validation</span
                  ><b>{{
                    issues.length ? issues.length + " to fix" : "Looking good"
                  }}</b>
                </div>
                <button class="text-button" @click="tab = 'checkout'">
                  Set up checkout ↗
                </button>
              </section>
              <section class="admin-section">
                <p class="eyebrow">YOUR SAFETY NET</p>
                <h2>Drafts & backups</h2>
                <p class="help-copy">
                  Edits stay in your browser until you publish. Export a backup
                  before making a big change. Tokens are excluded from catalog
                  backups.
                </p>
                <div class="admin-actions">
                  <button class="button small" @click="exportCatalog">
                    Export JSON ↓</button
                  ><label class="button small import-button"
                    >Import backup ↑<input
                      type="file"
                      accept=".json,application/json"
                      @change="importCatalog" /></label
                  ><button
                    class="text-button"
                    :disabled="!dirty"
                    @click="discard"
                  >
                    Discard edits</button
                  ><button
                    v-if="connected"
                    class="text-button"
                    @click="refreshCatalog"
                  >
                    Update from GitHub · keep edits ↻
                  </button>
                </div>
                <p class="help-copy">
                  {{
                    draftMessage || "Your catalog is loaded and ready to edit."
                  }}
                </p>
              </section>
            </div>
          </template>
          <template v-if="tab === 'products'">
            <template v-if="!selected"
              ><div class="admin-toolbar">
                <label class="search-field"
                  ><span class="sr-only">Search products</span
                  ><input
                    v-model="search"
                    type="search"
                    placeholder="Search by name, SKU or ID…" /></label
                ><select
                  v-model="categoryFilter"
                  aria-label="Filter department"
                >
                  <option value="">All departments</option>
                  <option
                    v-for="c in catalog.categories"
                    :key="c.id"
                    :value="c.id"
                  >
                    {{ c.name }}
                  </option></select
                ><select v-model="stateFilter" aria-label="Filter status">
                  <option value="">All statuses</option>
                  <option value="available">Available</option>
                  <option value="coming-soon">Coming soon</option>
                  <option value="sold-out">Sold out</option>
                  <option value="hidden">Hidden</option></select
                ><button class="button primary small" @click="addProduct">
                  Add product +
                </button>
              </div>
              <div class="product-table-wrap">
                <table class="admin-table">
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Department</th>
                      <th>Price / USD</th>
                      <th>Status</th>
                      <th>Stock</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="p in filtered" :key="p.id">
                      <td>
                        <button class="table-product" @click="selected = p">
                          <img
                            v-if="p.coverImage"
                            :src="productImageUrl(p.coverImage)"
                            :alt="p.name"
                          /><span v-else class="table-art"
                            ><RoddyLogo kind="badge" /></span
                          ><span
                            ><strong>{{ p.name }}</strong
                            ><small
                              >{{ p.sku }}
                              <span v-if="p.featured">/ FEATURED</span></small
                            ></span
                          >
                        </button>
                      </td>
                      <td>
                        {{
                          catalog.categories.find((c) => c.id === p.category)
                            ?.name
                        }}
                        <small v-if="!categoryVisible(catalog.categories.find(c => c.id === p.category))" class="help-copy"> · Unlisted</small>
                      </td>
                      <td>
                        {{ priceLabel(p) }}
                      </td>
                      <td>
                        <span class="table-status" :class="p.status">{{
                          !p.active ? "Hidden" : p.status.replace("-", " ")
                        }}</span>
                      </td>
                      <td>{{ p.merch ? "Printify variants" : p.trackStock ? p.stock : "Unlimited" }}</td>
                      <td>
                        <div class="admin-actions">
                          <button
                            class="text-button"
                            :disabled="catalog.products.indexOf(p) === 0"
                            :aria-label="`Move ${p.name} up`"
                            @click="
                              move(
                                catalog.products,
                                catalog.products.indexOf(p),
                                -1,
                              )
                            "
                          >
                            ↑</button
                          ><button
                            class="text-button"
                            :disabled="
                              catalog.products.indexOf(p) ===
                              catalog.products.length - 1
                            "
                            :aria-label="`Move ${p.name} down`"
                            @click="
                              move(
                                catalog.products,
                                catalog.products.indexOf(p),
                                1,
                              )
                            "
                          >
                            ↓</button
                          ><button class="text-button" @click="selected = p">
                            Edit ↗
                          </button>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <p v-if="!filtered.length" class="empty-state">
                  No products match your filters.
                </p>
              </div>
              <p class="help-copy">
                {{ filtered.length }} products · Edit a product for pricing,
                galleries, tags and download links.
              </p></template
            >
            <ProductEditor
              v-else
              :key="catalog.products.indexOf(selected)"
              :product="selected"
              :catalog="catalog"
              :library="library"
              :token="form.token"
              @close="selected = null"
              @duplicate="duplicate"
              @delete="removeProduct"
              @media-busy="pendingMedia += $event ? 1 : -1"
            />
          </template>
          <KeycapManager v-if="tab === 'keycaps'" :catalog="catalog" :endpoint="catalog.settings.checkoutEndpoint" :token="form.token" :connected="connected" @edit-product="selected=$event;tab='products'" @open-orders="tab='orders'" />
          <CategoryManager v-if="tab === 'categories'" :catalog="catalog" />
          <template v-if="tab === 'tags'"
            ><div class="section-heading">
              <p class="help-copy">
                Create colored pills once, then assign them to any product.
                Labels and colors update everywhere.
              </p>
              <button class="button primary small" @click="addTag">
                Add tag +
              </button>
            </div>
            <div class="admin-two-col">
              <section
                v-for="t in catalog.tags"
                :key="t.id"
                class="admin-section"
              >
                <ProductTags :ids="[t.id]" :definitions="catalog.tags" />
                <div class="form-grid">
                  <label>Label<input v-model="t.label" /></label
                  ><label
                    >Pill color<input v-model="t.color" type="color"
                  /></label>
                </div>
                <p class="help-copy">
                  {{
                    catalog.products.filter((p) => p.tags.includes(t.id)).length
                  }}
                  products use this tag
                </p>
                <button class="text-button" @click="removeTag(t)">
                  Remove tag
                </button>
              </section>
            </div></template
          >
          <template v-if="tab === 'homepage'"
            ><div class="admin-two-col">
              <section class="admin-section">
                <p class="eyebrow">FIRST IMPRESSIONS</p>
                <h2>Landing page</h2>
                <label
                  >Announcement bar<input
                    v-model="catalog.settings.announcement" /></label
                ><label
                  >Eyebrow<input
                    v-model="catalog.settings.heroEyebrow" /></label
                ><label
                  >Main headline<textarea
                    v-model="catalog.settings.heroTitle"
                    rows="3"
                  /></label
                ><label
                  >Introduction<textarea
                    v-model="catalog.settings.heroDescription"
                    rows="4"
                  /></label
                ><label
                  >Catalog button label<input
                    v-model="catalog.settings.heroButton" /></label
                ><label
                  >Featured lineup heading<input
                    v-model="catalog.settings.featuredTitle"
                /></label>
              </section>
              <section class="admin-section">
                <p class="eyebrow">THE MAIN AT-A-GLANCE IMAGE</p>
                <h2>Product spotlight</h2>
                <label
                  >Spotlight product<select
                    v-model="catalog.settings.heroProductId"
                  >
                    <option value="">No spotlight product</option>
                    <option
                      v-for="p in catalog.products.filter((p) => p.active)"
                      :key="p.id"
                      :value="p.id"
                    >
                      {{ p.name }}
                    </option>
                  </select></label
                >
                <p class="help-copy">
                  Uses this product's cover by default. Set a separate image
                  below to override it for the landing page. This product also
                  appears in the shop's featured exhibit, using its cover image.
                  Choose “No spotlight product” to hide both.
                </p>
                <MediaEditor
                  v-model="heroImages"
                  single
                  title="Landing page image override"
                  :library="library"
                  @busy="pendingMedia += $event ? 1 : -1"
                /><button class="button small" @click="preview">
                  Preview your homepage ↗
                </button>
              </section>
              <section class="admin-section">
                <h2>The RODDY manifesto</h2>
                <label
                  >Headline<textarea
                    v-model="catalog.settings.manifestoTitle"
                    rows="3"
                  /></label
                ><label
                  >Story<textarea
                    v-model="catalog.settings.manifestoText"
                    rows="5"
                  />
                </label>
              </section>
              <section class="admin-section">
                <h2>Customer support</h2>
                <label
                  >Support email<input
                    v-model="catalog.settings.supportEmail"
                    type="email"
                    placeholder="you@roddy.world"
                /></label>
                <p class="help-copy">
                  Shown in the storefront footer. All homepage and product
                  layouts automatically follow your existing 14-colorway theme
                  selector.
                </p>
              </section>
            </div></template
          >
          <template v-if="tab === 'checkout'">
            <div class="admin-two-col">
              <section class="admin-section">
                <p class="eyebrow">SQUARE / SECURE CHECKOUT</p>
                <h2>Connect the store backend</h2>
                <p class="help-copy">
                  Square takes payment on its hosted checkout page. The droplet
                  verifies payment and delivers private software ZIPs.
                </p>
                <label
                  >Checkout server URL<input
                    v-model.trim="catalog.settings.checkoutEndpoint"
                    type="url"
                    placeholder="https://api.roddy.world"
                /></label>
                <div class="admin-actions">
                  <button
                    class="button small"
                    :disabled="commerceBusy"
                    @click="checkConnection"
                  >
                    Check connection
                  </button>
                  <span v-if="connectionStatus" class="help-copy"
                    >{{
                      connectionStatus.configured
                        ? "Key configured"
                        : "Key missing"
                    }}
                    ·
                    {{
                      connectionStatus.accountReady
                        ? "USD card processing ready"
                        : "Account setup needed"
                    }}
                    · {{ connectionStatus.mode }} mode ·
                    {{
                      connectionStatus.checkoutEnabled
                        ? "Server checkout enabled"
                        : "Server checkout disabled"
                    }}</span
                  >
                </div>
                <label class="check"
                  ><input
                    v-model="catalog.settings.checkoutEnabled"
                    type="checkbox"
                  />Enable customer checkout after a successful test
                  purchase</label
                >
                <p class="notice">
                  The frontend switch and the server switch must both be
                  enabled. Keep public checkout disabled while testing.
                </p>
              </section>
              <section class="admin-section setup-guide">
                <p class="eyebrow">ONE-TIME SERVER SETUP</p>
                <h2>Square and your droplet</h2>
                <ol>
                  <li>
                    Create a US Square seller account and link your payout bank
                    account.
                  </li>
                  <li>
                    Create a developer application. Configure the sandbox access
                    token and location ID in the droplet's private environment
                    file.
                  </li>
                  <li>
                    Deploy the backend as a separate systemd service behind
                    HTTPS. Install the release ZIP in its private files
                    directory.
                  </li>
                  <li>
                    Test payment, cancellation, retries, and paid download
                    delivery with the unpublished local preview.
                  </li>
                  <li>
                    Configure live credentials, verify the live account
                    connection, then enable checkout on the server and publish
                    the frontend settings.
                  </li>
                </ol>
                <p class="notice">
                  API credentials stay on the droplet. Never put them in the
                  public catalog or GitHub token field.
                </p>
                <a
                  href="https://developer.squareup.com/apps"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="button small"
                  >Square developer dashboard ↗</a
                >
              </section>
              <section class="admin-section">
                <h2>Digital delivery</h2>
                <p class="help-copy">
                  Checkout supports mixed carts with digital downloads, one copy
                  per product. Files are released only after server verification
                  of the correct USD payment. Download links last 15 minutes and
                  can be refreshed from the private order page for 30 days.
                </p>
                <p class="help-copy">
                  Promotions and automatic tax are not configured. Arrange applicable tax treatment before accepting
                  live payments.
                </p>
              </section>
              <section class="admin-section">
                <h2>Payments and support</h2>
                <p class="help-copy">
                  Use Square for receipts, customer details, and refunds. Orders
                  here show the latest payment status checked by this backend. A
                  refunded order cannot generate a new download.
                </p>
                <a
                  href="https://squareup.com/dashboard/sales/transactions"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="button small"
                  >Payments & refunds in Square ↗</a
                >
              </section>
            </div>
          </template>
          <template v-if="tab === 'printify'">
            <section class="admin-section">
              <h2>Set up made-to-order merchandise</h2>
              <p class="help-copy">Connect Printify to prepare the RODDY hoodie and desk mat. Import actual color/size combinations, retail prices and standard shipping from your Printify products. Review your draft below, then publish it to the storefront. Checkout automatically submits paid merchandise orders and refreshes production and tracking.</p>
              <ol class="setup-list">
                <li>Create a Printify account and an API store named RODDY.</li>
                <li>In Printify Connections, generate a token with <code>shops.read</code>, <code>products.read</code> and <code>catalog.read</code>, <code>orders.read</code> and <code>orders.write</code>.</li>
                <li>Run the command below in your droplet console and enter the token at the hidden prompt.</li>
                <li>Create your hoodie and desk mat in that Printify store, upload the print artwork, and select the sizes and colors you want to sell.</li>
              </ol>
              <pre class="setup-command">python3 /opt/roddy-store/backend/deploy/configure-printify.py</pre>
              <p class="help-copy">Hoodie artwork: the full RODDY logo in white with a red dot, on a transparent 3531 × 2352 px canvas. Select a black hoodie and upload this file to the front print area.</p>
              <p><a class="button small" href="./downloads/merch/roddy-hoodie-white-red-front.png" download="RODDY-hoodie-white-red-front.png">Download hoodie print PNG ↓</a></p>
              <p class="help-copy">Desk-mat artwork follows the storefront ad: black, cream curves, red circle, and the original RODDY logo. Choose the file matching your selected SPOKE mat size. Each layout keeps the logo and curves in proportion. Apply a separate design to each size in Printify, then check the template bleed and safe area before ordering.</p>
              <div class="admin-actions">
                <a class="button small" href="./downloads/merch/roddy-deskmat-spoke-12x18-printify.png" download="RODDY-deskmat-spoke-12x18-printify.png">Desk mat 12 × 18 inches PNG ↓</a>
                <a class="button small" href="./downloads/merch/roddy-deskmat-spoke-12x22-printify.png" download="RODDY-deskmat-spoke-12x22-printify.png">Desk mat 12 × 22 inches PNG ↓</a>
                <a class="button small" href="./downloads/merch/roddy-deskmat-spoke-16x32.png" download="RODDY-deskmat-spoke-16x32.png">Desk mat 16 × 32 inches PNG ↓</a>
              </div>
              <div class="admin-actions">
                <a class="button small" href="https://printify.com/" target="_blank" rel="noopener noreferrer">Open Printify ↗</a>
                <a class="button small" href="https://help.printify.com/hc/en-us/articles/4483626447249-How-can-I-generate-an-API-token" target="_blank" rel="noopener noreferrer">Token setup guide ↗</a>
                <button class="button primary" :disabled="!connected || commerceBusy" @click="loadPrintify()">{{ commerceBusy ? "Loading…" : "Check connection & load products" }}</button>
              </div>
              <p v-if="!connected" class="help-copy">Connect to GitHub to access the private product list. Enter the Printify token only in the droplet console.</p>
              <p v-if="printifyStatus && !printifyStatus.configured" class="notice">Printify is not connected yet. Complete the droplet setup command above.</p>
              <template v-if="printifyStatus?.configured">
                <p class="notice">Connected to {{ printifyStatus.shop.title }} · {{ printifyStatus.shop.channel }}</p>
                <p v-if="!printifyStatus.products.length">No products found. Save your hoodie and desk-mat designs in this Printify store, then load products again.</p>
                <section v-for="product in printifyStatus.products" :key="product.id" class="admin-section">
                  <h3>{{ product.title }}</h3>
                  <p class="help-copy">Printify product: {{ product.id }}</p>
                  <p class="help-copy">{{ product.variants.filter(v => v.enabled).length }} enabled variants · {{ [...new Set(product.variants.filter(v => v.enabled).map(v => v.color).filter(Boolean))].length }} colors · {{ [...new Set(product.variants.filter(v => v.enabled).map(v => v.size).filter(Boolean))].join(', ') }}</p>
                  <div class="admin-actions">
                    <label>Storefront product<select v-model="printifyMapping[product.id]"><option value="">Choose a product…</option><option v-for="target in catalog.products.filter(p => p.type === 'physical')" :key="target.id" :value="target.id">{{ target.name }}</option></select></label>
                    <button class="button small" :disabled="commerceBusy || !printifyMapping[product.id]" @click="syncPrintify(product, printifyMapping[product.id])">Import options & shipping</button>
                  </div>
                </section>
                <div class="admin-actions">
                  <button v-if="printifyStatus.page > 1" class="button small" :disabled="commerceBusy" @click="loadPrintify(printifyStatus.page - 1)">Previous products</button>
                  <button v-if="printifyStatus.hasMore" class="button small" :disabled="commerceBusy" @click="loadPrintify(printifyStatus.page + 1)">More products</button>
                </div>
              </template>
              <section v-for="target in catalog.products.filter(p => p.merch)" :key="target.id" class="admin-section">
                <h2>{{ target.name }}</h2>
                <button class="button small" :disabled="!connected || commerceBusy" @click="syncPrintify({id: target.merch.productId}, target.id)">Refresh stock, costs & shipping</button>
                <p class="help-copy">Refreshing keeps your storefront retail prices and offer checkboxes. Size/color combinations disabled in Printify are removed; newly enabled combinations are imported.</p>
                <MerchEditor :product="target" :live-product="livePrintifyProducts[target.id]" />
              </section>
              <p class="help-copy">Customers can combine merchandise and downloads in one checkout. The backend quotes shipping for their address, verifies payment, submits Printify orders and refreshes tracking. Printify charges production and shipping to your Printify account separately; keep its payment method funded. Review exceptions in Orders.</p>
            </section>
          </template>
          <ProjectWorkshop v-if="tab === 'workshop'" :endpoint="catalog.settings.checkoutEndpoint" :token="form.token" :connected="connected" />
          <template v-if="tab === 'pcb'"><PcbWizard :endpoint="catalog.settings.checkoutEndpoint" :token="form.token" :connected="connected" :products="catalog.products" /></template>
          <template v-if="tab === 'orders'"><OrderManager :refresh-key="ordersRefresh" :endpoint="catalog.settings.checkoutEndpoint" :token="form.token" :connected="connected" /></template>
          <template v-if="tab === 'customers'"><CustomerManager :endpoint="catalog.settings.checkoutEndpoint" :token="form.token" :connected="connected" /></template>
          <div v-show="tab === 'suppliers'"><SupplierManager @navigate="tab = $event" :catalog="catalog" :token="form.token" :connected="connected" @import-products="catalog.products.push(...$event)" @edit-product="selected = $event; tab = 'products'" /></div>
          <div v-show="tab === 'newsletters'"><NewsletterManager :endpoint="catalog.settings.checkoutEndpoint" :token="form.token" :connected="connected" :github="form" :library="library" :products="catalog.products" /></div>
          <template v-if="tab === 'forum'"><ForumManager :endpoint="catalog.settings.checkoutEndpoint" :token="form.token" :connected="connected" /></template>

        </fieldset>
        <p v-else class="empty-state">Loading your control desk…</p>
        <footer class="admin-footer">
          <span>RODDY CONTROL DESK / BUILT FOR BIG IDEAS</span
          ><span>{{ draftMessage }}</span>
        </footer>
      </main>
    </div>
    <ThemeOverlay />
  </div>
</template>
