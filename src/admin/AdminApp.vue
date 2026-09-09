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
import { fetchCatalog, saveCatalog, uploadFile, listRepoImages } from "./api";
import { commerceRequest } from "./commerce-api";
import { blankProduct, slugify } from "./utils";
import { dataUrlToBase64 } from "./image";
import "./admin.css";

useThemeStore();
const ui = useUiStore();
const CONFIG_KEY = "roddy:admin:config";
const tab = ref("overview");
const tabs = [
  { id: "overview", label: "Overview", icon: "◫" },
  { id: "products", label: "Products", icon: "▦" },
  { id: "categories", label: "Departments", icon: "⌘" },
  { id: "tags", label: "Tags & colors", icon: "◉" },
  { id: "homepage", label: "Homepage", icon: "↗" },
  { id: "checkout", label: "Checkout & Stripe", icon: "▣" },
  { id: "promotions", label: "Promo codes", icon: "◇" },
  { id: "orders", label: "Orders", icon: "▤" },
];
const form = reactive({
  owner: "lionsarmor",
  repo: "RODDY-STORE-FRONT",
  branch: "main",
  token: "",
  remember: false,
});
const connected = ref(false);
const showConnection = ref(false);
const catalog = ref(null);
const sha = ref(null);
const baseline = ref("");
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
const promos = ref([]);
const orders = ref([]);
const ordersCursor = ref("");
const ordersHasMore = ref(false);
const promo = reactive({
  code: "",
  percent: 10,
  maxRedemptions: "",
  expiresAt: "",
});
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
          ? !p.active
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
    value: catalog.value?.products.filter((p) => p.active).length || 0,
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
    label: "Departments",
    value: catalog.value?.categories.length || 0,
    tab: "categories",
  },
]);
let draftTimer;
function installCatalog(data, nextSha = null) {
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
    if (keepDraft) {
      sha.value = result.sha;
      baseline.value = JSON.stringify(normalizeCatalog(result.catalog));
    } else installCatalog(result.catalog, result.sha);
    connected.value = true;
    showConnection.value = false;
    status.value = keepDraft
      ? "Connected. Your local draft was kept; publishing will replace the current GitHub catalog with this draft."
      : "Connected. You can publish changes to GitHub.";
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
  orders.value = [];
  promos.value = [];
}
async function refreshCatalog() {
  if (
    dirty.value &&
    !confirm(
      "Reload the published catalog and discard your current draft? Export a backup first to keep it.",
    )
  )
    return;
  saving.value = true;
  error.value = "";
  try {
    const result = await fetchCatalog(form);
    installCatalog(result.catalog, result.sha);
    clearTimeout(draftTimer);
    localStorage.removeItem(draftKey.value);
    draftAvailable.value = false;
    status.value = "Reloaded the latest published catalog.";
  } catch (e) {
    error.value = e.message;
  } finally {
    saving.value = false;
  }
}
function restoreDraft() {
  try {
    const draft = JSON.parse(localStorage.getItem(draftKey.value));
    if (!draft?.catalog) throw new Error("No saved draft found.");
    if (connected.value && draft.sha !== sha.value)
      throw new Error(
        "The published catalog has changed since this draft. Export the draft and merge it with the latest catalog before publishing.",
      );
    catalog.value = normalizeCatalog(draft.catalog);
    selected.value = null;
    draftAvailable.value = false;
    status.value = "Draft restored. Review it before publishing.";
  } catch (e) {
    error.value = e.message;
  }
}
function discard() {
  if (!confirm("Discard all edits since this catalog was loaded or published?"))
    return;
  clearTimeout(draftTimer);
  catalog.value = JSON.parse(baseline.value);
  selected.value = null;
  localStorage.removeItem(draftKey.value);
  draftAvailable.value = false;
  draftMessage.value = "";
  status.value = "Draft discarded.";
}
async function publish() {
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
  const snapshot = JSON.parse(JSON.stringify(catalog.value));
  try {
    if (
      /(?:sk_(?:live|test)_|github_pat_|ghp_)[a-zA-Z0-9_]{10,}/.test(
        JSON.stringify(snapshot),
      )
    )
      throw new Error(
        "A secret token was found in the catalog. Remove it from public fields before publishing.",
      );
    const sources = new Set();
    for (const p of snapshot.products)
      [p.coverImage, ...p.images].forEach((src) => {
        if (src?.startsWith("data:")) sources.add(src);
      });
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
function addCategory() {
  catalog.value.categories.push({
    id: uniqueId("new-department", catalog.value.categories),
    name: "New department",
    code: "",
  });
}
function removeCategory(c) {
  if (catalog.value.products.some((p) => p.category === c.id)) {
    error.value =
      "Move products to another department before deleting this one.";
    return;
  }
  catalog.value.categories = catalog.value.categories.filter(
    (item) => item !== c,
  );
}
function move(list, i, direction) {
  const target = i + direction;
  if (target >= 0 && target < list.length)
    [list[i], list[target]] = [list[target], list[i]];
}
function renameCategory(c, value) {
  const previous = c.id;
  c.id = slugify(value);
  catalog.value.products.forEach((p) => {
    if (p.category === previous) p.category = c.id;
  });
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
    new Blob([JSON.stringify(catalog.value, null, 2)], {
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
async function loadPromos() {
  const data = await commerceRequest(
    catalog.value.settings.checkoutEndpoint,
    "/admin/promotions",
    form.token,
  );
  promos.value = data.data || [];
}
function createPromo() {
  commerce(async () => {
    await commerceRequest(
      catalog.value.settings.checkoutEndpoint,
      "/admin/promotions",
      form.token,
      {
        code: promo.code,
        percent: promo.percent,
        maxRedemptions: promo.maxRedemptions
          ? Number(promo.maxRedemptions)
          : null,
        expiresAt: promo.expiresAt
          ? new Date(promo.expiresAt).toISOString()
          : null,
      },
    );
    promo.code = "";
    status.value = "Promotion created in Stripe.";
    await loadPromos();
  });
}
function togglePromo(p) {
  commerce(async () => {
    await commerceRequest(
      catalog.value.settings.checkoutEndpoint,
      "/admin/promotions/" + p.id,
      form.token,
      { active: !p.active },
    );
    await loadPromos();
  });
}
function loadOrders(more = false) {
  commerce(async () => {
    const data = await commerceRequest(
      catalog.value.settings.checkoutEndpoint,
      "/admin/orders" +
        (more && ordersCursor.value
          ? "?after=" + encodeURIComponent(ordersCursor.value)
          : ""),
      form.token,
    );
    orders.value = more ? [...orders.value, ...data.data] : data.data;
    ordersHasMore.value = data.has_more;
    ordersCursor.value = data.next_cursor || "";
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
            }}</span>
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
            @click="restoreDraft"
          >
            Restore draft</button
          ><button class="text-button" @click="draftAvailable = false">
            Dismiss
          </button>
        </div>
        <details v-if="issues.length" class="notice validation-list">
          <summary>
            {{ issues.length }} item(s) need attention before publishing
          </summary>
          <ul>
            <li v-for="issue in issues" :key="issue">{{ issue }}</li>
          </ul>
        </details>
        <fieldset v-if="catalog" :disabled="saving" class="admin-workspace">
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
              <RoddyLogo kind="badge" class="admin-welcome-logo" aria-hidden="true" />
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
                  <span>Stripe checkout</span
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
                    Reload from GitHub ↻
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
                          /><span v-else class="table-art"><RoddyLogo kind="badge" /></span
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
                      </td>
                      <td>
                        {{ p.pricePending ? "TBA" : formatPrice(p.price) }}
                      </td>
                      <td>
                        <span class="table-status" :class="p.status">{{
                          !p.active ? "Hidden" : p.status.replace("-", " ")
                        }}</span>
                      </td>
                      <td>{{ p.trackStock ? p.stock : "Unlimited" }}</td>
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
              @close="selected = null"
              @duplicate="duplicate"
              @delete="removeProduct"
              @media-busy="pendingMedia += $event ? 1 : -1"
            />
          </template>
          <template v-if="tab === 'categories'"
            ><div class="section-heading">
              <p class="help-copy">
                Departments control navigation and catalog filtering. Reorder
                them to change their order across the storefront.
              </p>
              <button class="button primary small" @click="addCategory">
                Add department +
              </button>
            </div>
            <section
              v-for="(c, i) in catalog.categories"
              :key="i"
              class="admin-section category-row"
            >
              <span class="category-index">{{
                String(i + 1).padStart(2, "0")
              }}</span
              ><label>Name<input v-model="c.name" /></label
              ><label
                >ID<input
                  :value="c.id"
                  @change="renameCategory(c, $event.target.value)" /></label
              ><label>Department caption<input v-model="c.code" /></label
              ><span class="help-copy"
                >{{
                  catalog.products.filter((p) => p.category === c.id).length
                }}
                products</span
              >
              <div class="admin-actions">
                <button
                  class="button small"
                  :disabled="i === 0"
                  aria-label="Move department up"
                  @click="move(catalog.categories, i, -1)"
                >
                  ↑</button
                ><button
                  class="button small"
                  :disabled="i === catalog.categories.length - 1"
                  aria-label="Move department down"
                  @click="move(catalog.categories, i, 1)"
                >
                  ↓</button
                ><button class="button small" @click="removeCategory(c)">
                  Delete
                </button>
              </div>
            </section></template
          >
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
                  below to override it for the landing page.
                  This product also appears in the shop's featured exhibit,
                  using its cover image. Choose “No spotlight product” to hide both.
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
          <template v-if="tab === 'checkout'"
            ><div class="admin-two-col">
              <section class="admin-section">
                <p class="eyebrow">STRIPE / SECURE CHECKOUT</p>
                <h2>Get ready to take orders</h2>
                <p class="help-copy">
                  Customers pay through Stripe-hosted checkout. Your bank
                  account and payout details belong in your Stripe account.
                </p>
                <a
                  href="https://dashboard.stripe.com/account/onboarding"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="button"
                  >Set up your Stripe account ↗</a
                ><label
                  >Checkout server URL<input
                    v-model.trim="catalog.settings.checkoutEndpoint"
                    type="url"
                    placeholder="https://roddy-checkout.yourname.workers.dev"
                /></label>
                <div class="admin-actions">
                  <button
                    class="button small"
                    :disabled="commerceBusy"
                    @click="checkConnection"
                  >
                    Check connection</button
                  ><span v-if="connectionStatus" class="help-copy"
                    >{{
                      connectionStatus.stripeConfigured
                        ? "Stripe key configured"
                        : "Stripe key missing"
                    }}
                    · {{ connectionStatus.mode }} mode</span
                  >
                </div>
                <label class="check"
                  ><input
                    v-model="catalog.settings.checkoutEnabled"
                    type="checkbox"
                  />Enable customer checkout after a successful test
                  purchase</label
                ><label class="check"
                  ><input
                    v-model="catalog.settings.allowPromotionCodes"
                    type="checkbox"
                  />Allow promo codes at Stripe checkout</label
                ><label class="check"
                  ><input
                    v-model="catalog.settings.automaticTax"
                    type="checkbox"
                  />Enable Stripe Tax (configure tax registrations in Stripe
                  first)</label
                >
              </section>
              <section class="admin-section setup-guide">
                <p class="eyebrow">ONE-TIME SERVER SETUP</p>
                <h2>Connect your account securely</h2>
                <ol>
                  <li>
                    Open Stripe Developers → API keys and start with a test
                    secret key.
                  </li>
                  <li>
                    In this project's <code>worker</code> directory, run
                    <code>npm install</code>, then
                    <code>npx wrangler login</code>.
                  </li>
                  <li>
                    Run
                    <code>npx wrangler secret put STRIPE_SECRET_KEY</code> and
                    paste your key at the terminal prompt.
                  </li>
                  <li>
                    Run <code>npm run deploy</code>. Copy the resulting server
                    URL into the field on the left.
                  </li>
                  <li>
                    Publish the catalog, check the connection, enable checkout,
                    and place a test order. Replace the server secret with your
                    live key only when ready.
                  </li>
                </ol>
                <p class="notice">
                  The secret key is stored on Cloudflare, never in this public
                  catalog. Admin orders and promotions use your GitHub sign-in.
                </p>
                <a
                  href="https://dashboard.stripe.com/test/apikeys"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-button"
                  >Open Stripe test keys ↗</a
                >
              </section>
              <section class="admin-section">
                <h2>Shipping</h2>
                <label
                  >Countries served<input
                    v-model="catalog.settings.shippingCountries"
                    placeholder="US,CA"
                  /><small
                    >Comma-separated two-letter country codes.</small
                  ></label
                >
                <div class="form-grid">
                  <label
                    >Flat shipping price (USD)<input
                      v-model.number="catalog.settings.shippingRate"
                      type="number"
                      min="0"
                      step=".01" /></label
                  ><label
                    >Shipping name<input
                      v-model="catalog.settings.shippingLabel"
                  /></label>
                </div>
                <p class="help-copy">
                  Shipping is added once per order containing physical items.
                  Digital-only orders skip shipping and delivery address
                  collection.
                </p>
              </section>
              <section class="admin-section">
                <h2>Fulfillment</h2>
                <p class="help-copy">
                  Review paid orders in the Orders panel. This storefront uses
                  manual stock counts and fulfillment. It does not reserve
                  inventory, decrement stock automatically, or deliver paid
                  files. Review stock before going live and after each order.
                </p>
                <a
                  href="https://dashboard.stripe.com/payments"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="button small"
                  >Payments & refunds in Stripe ↗</a
                >
              </section>
            </div></template
          >
          <template v-if="tab === 'promotions'"
            ><p class="notice">
              Promotions are saved directly in Stripe, independent of Publish.
              Connect GitHub and your checkout server first. Codes are entered
              by customers on the Stripe payment page.
            </p>
            <div class="admin-two-col">
              <form class="admin-section" @submit.prevent="createPromo">
                <h2>Create a promotion</h2>
                <label
                  >Code<input
                    v-model="promo.code"
                    required
                    pattern="[a-zA-Z0-9]{1,40}"
                    placeholder="RODDY10"
                /></label>
                <div class="form-grid">
                  <label
                    >Discount (%)<input
                      v-model.number="promo.percent"
                      type="number"
                      min="1"
                      max="100"
                      required /></label
                  ><label
                    >Maximum uses<input
                      v-model="promo.maxRedemptions"
                      type="number"
                      min="1"
                      placeholder="Unlimited" /></label
                  ><label class="full"
                    >Expires (your local time)<input
                      v-model="promo.expiresAt"
                      type="datetime-local"
                  /></label>
                </div>
                <button
                  class="button primary"
                  :disabled="!connected || commerceBusy"
                >
                  Create in Stripe +
                </button>
              </form>
              <section class="admin-section">
                <div class="field-heading">
                  <h2>Your promo codes</h2>
                  <button
                    class="text-button"
                    :disabled="!connected || commerceBusy"
                    @click="commerce(loadPromos)"
                  >
                    Refresh ↻
                  </button>
                </div>
                <p v-if="!promos.length" class="help-copy">
                  Refresh to load your Stripe promotions. Connect Stripe to
                  create your first code.
                </p>
                <div v-for="p in promos" :key="p.id" class="promo-row">
                  <div>
                    <strong>{{ p.code }}</strong
                    ><small
                      >{{ p.percent_off ?? "—" }}% off ·
                      {{ p.times_redeemed }} uses{{
                        p.max_redemptions ? " / " + p.max_redemptions : ""
                      }}
                      · {{ p.active ? "Active" : "Inactive" }}</small
                    >
                  </div>
                  <button
                    class="button small"
                    :disabled="commerceBusy"
                    @click="togglePromo(p)"
                  >
                    {{ p.active ? "Disable" : "Enable" }}
                  </button>
                </div>
              </section>
            </div></template
          >
          <template v-if="tab === 'orders'"
            ><div class="section-heading">
              <p class="help-copy">
                Stripe checkout sessions, newest first. Only “paid” or “no
                payment required” sessions are ready for manual fulfillment. Use
                Stripe for customer details, receipts and refunds.
              </p>
              <div class="admin-actions">
                <button
                  class="button small"
                  :disabled="!connected || commerceBusy"
                  @click="loadOrders()"
                >
                  {{ commerceBusy ? "Loading…" : "Load orders ↻" }}</button
                ><a
                  href="https://dashboard.stripe.com/payments"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="button small"
                  >Open Stripe ↗</a
                >
              </div>
            </div>
            <div class="product-table-wrap">
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Reference</th>
                    <th>Customer</th>
                    <th>Total</th>
                    <th>Payment</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="order in orders" :key="order.id">
                    <td>
                      {{ new Date(order.created * 1000).toLocaleDateString() }}
                    </td>
                    <td>{{ order.id.slice(-12) }}</td>
                    <td>{{ order.customer_details?.email || "—" }}</td>
                    <td>
                      {{
                        new Intl.NumberFormat("en-US", {
                          style: "currency",
                          currency: order.currency || "USD",
                        }).format((order.amount_total || 0) / 100)
                      }}
                    </td>
                    <td>{{ order.payment_status.replaceAll("_", " ") }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-if="!orders.length" class="empty-state">
                Connect your checkout server, then load orders to see real
                transactions here.
              </p>
            </div>
            <button
              v-if="ordersHasMore"
              class="button"
              :disabled="commerceBusy"
              @click="loadOrders(true)"
            >
              Load older orders
            </button></template
          >
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
