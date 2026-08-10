<script setup>
import { reactive, ref, computed, onMounted } from "vue";
import RoddyLogo from "../components/RoddyLogo.vue";
import SpectrumLoader from "../components/SpectrumLoader.vue";
import { useThemeStore } from "../stores/theme";
import { productImageUrl } from "../stores/catalog";
import { fetchCatalog, saveCatalog, uploadFile, listRepoImages } from "./api";
import { slugify, specsToText, textToSpecs, blankProduct, blankCategory } from "./utils";
import { compressImage, dataUrlToBase64 } from "./image";
import { normalizeProduct } from "../stores/catalog";

useThemeStore(); // side-effect: theme CSS vars stay active on this page too

const CONFIG_KEY = "roddy:admin:config";
const NEW_PRODUCT_ID = /^new-product(-\d+)?$/;
const NEW_CATEGORY_ID = /^new-category(-\d+)?$/;

const connected = ref(false);
const form = reactive({ owner: "", repo: "", branch: "main", token: "", remember: false });
const session = reactive({ sha: null, catalog: null });
const specsDraft = reactive({}); // productId -> raw textarea text, committed on blur
const imageErrors = reactive({}); // productId -> error message from a failed file read

// A product's `images` entries are either a committed repo path or a
// data: URL staged locally and not yet uploaded — isPendingImage tells them
// apart so the gallery and the publish step both know which is which.
function isPendingImage(src) {
  return typeof src === "string" && src.startsWith("data:");
}
const repoImages = ref([]); // image paths already committed under public/img/
const loadingRepoImages = ref(false);

const connectStatus = reactive({ text: "", kind: "" });
const editorStatus = reactive({ text: "", kind: "" });
const saveStatus = reactive({ text: "", kind: "" });
const saving = ref(false);

const targetLabel = computed(() => `${form.owner}/${form.repo}@${form.branch}:public/data/products.json`);

onMounted(() => {
  let saved = null;
  try {
    saved = JSON.parse(localStorage.getItem(CONFIG_KEY) || "null");
  } catch (e) {
    /* ignore */
  }

  if (saved) {
    form.owner = saved.owner || "";
    form.repo = saved.repo || "";
    form.branch = saved.branch || "main";
    if (saved.token) {
      form.token = saved.token;
      form.remember = true;
    }
    return;
  }

  const host = location.hostname;
  if (host.endsWith(".github.io")) {
    form.owner = host.replace(".github.io", "");
    const seg = location.pathname.split("/").filter(Boolean)[0];
    if (seg) form.repo = seg;
  }
});

function persistConfig() {
  if (!form.remember) {
    localStorage.removeItem(CONFIG_KEY);
    return;
  }
  localStorage.setItem(
    CONFIG_KEY,
    JSON.stringify({ owner: form.owner, repo: form.repo, branch: form.branch, token: form.token })
  );
}

function seedSpecsDrafts() {
  Object.keys(specsDraft).forEach((k) => delete specsDraft[k]);
  session.catalog.products.forEach((p) => {
    specsDraft[p.id] = specsToText(p.specs);
  });
}

async function loadRepoImages() {
  loadingRepoImages.value = true;
  try {
    repoImages.value = await listRepoImages(form);
  } catch (err) {
    editorStatus.text = err.message;
    editorStatus.kind = "error";
  } finally {
    loadingRepoImages.value = false;
  }
}

async function connect() {
  if (!form.owner || !form.repo || !form.token) {
    connectStatus.text = "Owner, repo and token are required.";
    connectStatus.kind = "error";
    return;
  }
  connectStatus.text = "Connecting…";
  connectStatus.kind = "";
  try {
    const { sha, catalog } = await fetchCatalog(form);
    catalog.products = catalog.products.map(normalizeProduct);
    session.sha = sha;
    session.catalog = catalog;
    seedSpecsDrafts();
    persistConfig();
    connectStatus.text = "Connected.";
    connectStatus.kind = "ok";
    connected.value = true;
    loadRepoImages(); // not awaited — fills in whenever it lands, doesn't block the editor
  } catch (err) {
    connectStatus.text = err.message;
    connectStatus.kind = "error";
  }
}

async function reload() {
  editorStatus.text = "Reloading…";
  editorStatus.kind = "";
  try {
    const { sha, catalog } = await fetchCatalog(form);
    catalog.products = catalog.products.map(normalizeProduct);
    session.sha = sha;
    session.catalog = catalog;
    seedSpecsDrafts();
    loadRepoImages();
    editorStatus.text = "Reloaded from GitHub.";
    editorStatus.kind = "ok";
  } catch (err) {
    editorStatus.text = err.message;
    editorStatus.kind = "error";
  }
}

async function save() {
  saving.value = true;
  saveStatus.text = "Publishing…";
  saveStatus.kind = "";
  try {
    const pendingUploads = [];
    session.catalog.products.forEach((product) => {
      (product.images || []).forEach((src, idx) => {
        if (isPendingImage(src)) pendingUploads.push({ product, idx, src });
      });
    });

    for (let i = 0; i < pendingUploads.length; i++) {
      const { product, idx, src } = pendingUploads[i];
      saveStatus.text = `Uploading photo ${i + 1} of ${pendingUploads.length}…`;
      const suffix = Math.random().toString(36).slice(2, 8);
      const path = `img/products/${product.id}-${suffix}.jpg`;
      await uploadFile(form, `public/${path}`, dataUrlToBase64(src));
      product.images[idx] = path;
    }

    saveStatus.text = "Publishing…";
    session.sha = await saveCatalog({ ...form, sha: session.sha }, session.catalog);
    saveStatus.text = "Published — live on the storefront within moments.";
    saveStatus.kind = "ok";
  } catch (err) {
    saveStatus.text = err.message;
    saveStatus.kind = "error";
  } finally {
    saving.value = false;
  }
}

function disconnect() {
  localStorage.removeItem(CONFIG_KEY);
  form.token = "";
  session.sha = null;
  session.catalog = null;
  connected.value = false;
  connectStatus.text = "Disconnected.";
  connectStatus.kind = "";
}

function addProduct() {
  const existingIds = new Set(session.catalog.products.map((p) => p.id));
  const product = blankProduct(existingIds);
  if (session.catalog.categories.length) product.category = session.catalog.categories[0].id;
  session.catalog.products.unshift(product);
  specsDraft[product.id] = "";
}

function deleteProduct(idx) {
  const p = session.catalog.products[idx];
  if (!confirm(`Delete "${p.name}" (${p.sku})? This can't be undone once published.`)) return;
  delete specsDraft[p.id];
  delete imageErrors[p.id];
  session.catalog.products.splice(idx, 1);
}

function onNameInput(product, value) {
  product.name = value;
  if (NEW_PRODUCT_ID.test(product.id)) product.id = slugify(value);
}

function commitSpecs(product) {
  product.specs = textToSpecs(specsDraft[product.id] || "");
}

async function onImagesSelected(product, event) {
  const files = Array.from(event.target.files || []);
  event.target.value = ""; // allow re-selecting the same file(s) later
  if (!files.length) return;
  delete imageErrors[product.id];
  for (const file of files) {
    try {
      product.images.push(await compressImage(file));
    } catch (err) {
      imageErrors[product.id] = err.message;
    }
  }
}

function addExistingImage(product, path) {
  if (!path) return;
  product.images.push(path);
}

function removeImageAt(product, idx) {
  product.images.splice(idx, 1);
}

function moveImage(product, idx, dir) {
  const target = idx + dir;
  if (target < 0 || target >= product.images.length) return;
  const images = product.images;
  [images[idx], images[target]] = [images[target], images[idx]];
}

function addCategory() {
  const existingIds = new Set(session.catalog.categories.map((c) => c.id));
  session.catalog.categories.push(blankCategory(existingIds));
}

function onCategoryNameInput(category, value) {
  category.name = value;
  if (NEW_CATEGORY_ID.test(category.id)) category.id = slugify(value);
}

function productCountFor(categoryId) {
  return session.catalog.products.filter((p) => p.category === categoryId).length;
}

function deleteCategory(idx) {
  const c = session.catalog.categories[idx];
  const count = productCountFor(c.id);
  if (count > 0) {
    alert(`"${c.name}" is still used by ${count} product${count === 1 ? "" : "s"}. Move ${count === 1 ? "it" : "them"} to another category first.`);
    return;
  }
  if (!confirm(`Delete category "${c.name}"? This can't be undone once published.`)) return;
  session.catalog.categories.splice(idx, 1);
}

function moveCategory(idx, dir) {
  const target = idx + dir;
  if (target < 0 || target >= session.catalog.categories.length) return;
  const list = session.catalog.categories;
  [list[idx], list[target]] = [list[target], list[idx]];
}
</script>

<template>
  <header class="border-b border-border bg-bg transition-colors duration-200">
    <div class="mx-auto flex max-w-6xl items-center gap-5 px-6 py-3">
      <a href="./index.html" class="flex items-center gap-2">
        <RoddyLogo kind="full_logo" class="h-8 w-auto" />
      </a>
      <nav class="flex-1">
        <span class="border border-brand px-2 py-1 font-mono text-[0.62rem] uppercase tracking-wide text-brand">
          Staff access
        </span>
      </nav>
      <a href="./index.html" class="border border-border px-3 py-2 font-mono text-xs uppercase tracking-wide hover:bg-bg-alt">
        ← Back to store
      </a>
    </div>
  </header>

  <main class="mx-auto max-w-6xl px-6 py-8">
    <div v-if="!connected" class="mx-auto max-w-lg text-center">
      <p class="text-3xl text-brand">●</p>
      <h1 class="mb-3 font-mono text-2xl uppercase tracking-wide">Inventory admin</h1>
      <p class="mb-6 text-text-dim">
        Connect with a GitHub token to load, edit and publish <code>public/data/products.json</code> directly to
        this repo. The storefront reads that file straight from GitHub, so changes go live within moments —
        no rebuild wait.
      </p>

      <div class="border border-border bg-panel p-6 text-left">
        <h2 class="mb-1 font-mono text-sm uppercase tracking-wide">Connect</h2>
        <p class="mb-5 max-w-[62ch] text-sm text-text-dim">
          Create a <strong>fine-grained personal access token</strong> at github.com → Settings → Developer
          settings → Personal access tokens, scoped to <em>only this repository</em> with
          <strong>Contents: Read and write</strong> permission. The token is used directly from your browser to
          call the GitHub API — it is never sent anywhere else, and is only kept on this device if you check
          "remember."
        </p>

        <div class="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label class="flex flex-col gap-1">
            <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">GitHub owner / org</span>
            <input v-model.trim="form.owner" type="text" placeholder="e.g. jamesmweeksjr" class="border border-border bg-bg-alt px-3 py-2 font-mono text-sm">
          </label>
          <label class="flex flex-col gap-1">
            <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">Repository</span>
            <input v-model.trim="form.repo" type="text" placeholder="e.g. RODDY-STORE-FRONT" class="border border-border bg-bg-alt px-3 py-2 font-mono text-sm">
          </label>
          <label class="flex flex-col gap-1">
            <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">Branch</span>
            <input v-model.trim="form.branch" type="text" class="border border-border bg-bg-alt px-3 py-2 font-mono text-sm">
          </label>
          <label class="flex flex-col gap-1">
            <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">Personal access token</span>
            <input v-model.trim="form.token" type="password" placeholder="github_pat_..." class="border border-border bg-bg-alt px-3 py-2 font-mono text-sm">
          </label>
        </div>

        <label class="mb-5 flex items-center gap-2">
          <input v-model="form.remember" type="checkbox">
          <span class="text-sm">Remember owner/repo/branch and token on this device</span>
        </label>

        <div class="flex flex-wrap items-center gap-3">
          <button
            type="button"
            class="border border-brand bg-brand px-5 py-3 font-mono text-xs uppercase tracking-wide text-white hover:opacity-90"
            @click="connect"
          >
            Connect
          </button>
          <span
            class="font-mono text-xs"
            :class="connectStatus.kind === 'ok' ? 'text-text' : connectStatus.kind === 'error' ? 'text-brand' : 'text-text-dim'"
          >
            {{ connectStatus.text }}
          </span>
        </div>
      </div>
    </div>

    <div v-else>
      <div class="border-b border-border pb-6">
        <h1 class="mb-2 font-mono text-2xl uppercase tracking-wide">Inventory</h1>
        <p class="text-text-dim">
          Editing <code>{{ targetLabel }}</code>. Add products, adjust price and stock, then publish.
        </p>
      </div>

      <div class="my-6 flex flex-wrap items-center gap-3">
        <button type="button" class="border border-brand bg-brand px-4 py-2 font-mono text-xs uppercase tracking-wide text-white hover:opacity-90" @click="addProduct">
          + Add product
        </button>
        <button type="button" class="border border-border px-4 py-2 font-mono text-xs uppercase tracking-wide hover:bg-bg-alt" @click="reload">
          ↺ Reload from GitHub
        </button>
        <button type="button" class="border border-border px-4 py-2 font-mono text-xs uppercase tracking-wide hover:bg-bg-alt" @click="disconnect">
          Disconnect
        </button>
        <span
          class="font-mono text-xs"
          :class="editorStatus.kind === 'ok' ? 'text-text' : editorStatus.kind === 'error' ? 'text-brand' : 'text-text-dim'"
        >
          {{ editorStatus.text }}
        </span>
      </div>

      <div class="mb-8 border border-border bg-panel p-5">
        <div class="mb-4 flex items-center justify-between gap-3">
          <h2 class="font-mono text-sm uppercase tracking-wide">Categories</h2>
          <button type="button" class="border border-border px-3 py-1.5 font-mono text-[0.65rem] uppercase tracking-wide hover:bg-bg-alt" @click="addCategory">
            + Add category
          </button>
        </div>

        <div v-if="!session.catalog.categories.length" class="font-mono text-sm text-text-dim">
          No categories yet — products need at least one to be filterable in the shop.
        </div>

        <div v-else class="flex flex-col gap-2">
          <div
            v-for="(c, idx) in session.catalog.categories"
            :key="c.id"
            class="grid grid-cols-1 items-center gap-3 border border-border bg-bg-alt p-3 sm:grid-cols-[1fr_1fr_max-content_max-content]"
          >
            <label class="flex flex-col gap-1">
              <span class="font-mono text-[0.6rem] uppercase tracking-wide text-text-dim">Name</span>
              <input :value="c.name" type="text" class="border border-border bg-panel px-2 py-1.5 font-mono text-sm" @input="onCategoryNameInput(c, $event.target.value)">
            </label>
            <label class="flex flex-col gap-1">
              <span class="font-mono text-[0.6rem] uppercase tracking-wide text-text-dim">Code (shown on homepage tiles)</span>
              <input v-model.trim="c.code" type="text" placeholder="e.g. RODDY GAMES" class="border border-border bg-panel px-2 py-1.5 font-mono text-sm">
            </label>
            <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">
              {{ productCountFor(c.id) }} product{{ productCountFor(c.id) === 1 ? "" : "s" }}
            </span>
            <div class="flex items-center gap-1 justify-self-start sm:justify-self-end">
              <button type="button" :disabled="idx === 0" class="border border-border px-2 py-1.5 font-mono text-xs disabled:opacity-30" title="Move up" @click="moveCategory(idx, -1)">↑</button>
              <button type="button" :disabled="idx === session.catalog.categories.length - 1" class="border border-border px-2 py-1.5 font-mono text-xs disabled:opacity-30" title="Move down" @click="moveCategory(idx, 1)">↓</button>
              <button type="button" class="border border-border px-2 py-1.5 font-mono text-[0.65rem] uppercase tracking-wide text-brand hover:border-brand hover:bg-brand hover:text-white" @click="deleteCategory(idx)">Delete</button>
            </div>
          </div>
        </div>
        <p class="mt-3 font-mono text-[0.65rem] text-text-dim">
          Reordering here changes the order categories appear on the homepage and in the shop filters. The top
          navigation's category links are fixed in code and won't pick up new categories automatically.
        </p>
      </div>

      <div v-if="!session.catalog.products.length" class="border border-dashed border-border p-10 text-center font-mono text-text-dim">
        No products yet. Click "+ Add product" to create the first one.
      </div>

      <div class="flex flex-col gap-4">
        <div v-for="(p, idx) in session.catalog.products" :key="p.id" class="border border-border bg-panel p-5">
          <div class="mb-4 flex items-center justify-between gap-3">
            <span class="font-mono text-sm uppercase tracking-wide text-text-dim">
              {{ p.sku || "R-???" }} · {{ p.active === false ? "Hidden" : "Live" }}
            </span>
            <button
              type="button"
              class="border border-border px-3 py-1.5 font-mono text-[0.65rem] uppercase tracking-wide text-brand hover:border-brand hover:bg-brand hover:text-white"
              @click="deleteProduct(idx)"
            >
              Delete
            </button>
          </div>

          <div class="mb-4 flex flex-col gap-3">
            <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">
              Photos ({{ p.images.length }}) — first is the cover shown on the catalog card
            </span>

            <div v-if="!p.images.length" class="bg-spec-grid relative flex h-24 w-24 items-center justify-center border border-border">
              <RoddyLogo kind="badge" class="w-[62%]" />
            </div>

            <div v-else class="flex flex-wrap gap-3">
              <div
                v-for="(src, iidx) in p.images"
                :key="iidx"
                class="bg-spec-grid relative flex h-24 w-24 flex-shrink-0 items-center justify-center border-2"
                :class="iidx === 0 ? 'border-brand' : 'border-border'"
              >
                <img :src="isPendingImage(src) ? src : productImageUrl(src)" alt="" class="h-full w-full object-cover">
                <span
                  v-if="iidx === 0"
                  class="absolute left-1 top-1 border border-brand bg-panel px-1 font-mono text-[0.55rem] uppercase tracking-wide text-brand"
                >
                  Cover
                </span>
                <div class="absolute inset-x-0 bottom-0 flex items-center justify-between bg-panel/90 px-1 py-0.5">
                  <button
                    type="button"
                    :disabled="iidx === 0"
                    class="font-mono text-[0.65rem] disabled:opacity-20"
                    title="Move earlier"
                    @click="moveImage(p, iidx, -1)"
                  >
                    ←
                  </button>
                  <button
                    type="button"
                    class="font-mono text-[0.65rem] text-brand"
                    title="Remove this photo"
                    @click="removeImageAt(p, iidx)"
                  >
                    ✕
                  </button>
                  <button
                    type="button"
                    :disabled="iidx === p.images.length - 1"
                    class="font-mono text-[0.65rem] disabled:opacity-20"
                    title="Move later"
                    @click="moveImage(p, iidx, 1)"
                  >
                    →
                  </button>
                </div>
              </div>
            </div>

            <label class="flex flex-col gap-1">
              <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">Add photo(s)</span>
              <input type="file" accept="image/*" multiple class="font-mono text-xs" @change="onImagesSelected(p, $event)">
            </label>

            <div class="flex items-center justify-between">
              <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">Or add a file already in the repo</span>
              <button type="button" class="font-mono text-[0.6rem] text-text-dim underline hover:text-brand" @click="loadRepoImages">
                {{ loadingRepoImages ? "Loading…" : "↻ Refresh list" }}
              </button>
            </div>
            <select
              class="border border-border bg-bg-alt px-2 py-1.5 font-mono text-xs"
              @change="addExistingImage(p, $event.target.value); $event.target.value = ''"
            >
              <option value="">{{ repoImages.length ? "Choose a file…" : "No files loaded yet — click Refresh" }}</option>
              <option v-for="path in repoImages" :key="path" :value="path">{{ path }}</option>
            </select>
            <input
              type="text"
              placeholder="or type/paste a path and press Enter, e.g. img/products/example.jpg"
              class="border border-border bg-bg-alt px-2 py-1.5 font-mono text-xs"
              @keydown.enter.prevent="addExistingImage(p, $event.target.value.trim()); $event.target.value = ''"
            >

            <p v-if="imageErrors[p.id]" class="max-w-[46ch] font-mono text-[0.65rem] text-brand">{{ imageErrors[p.id] }}</p>
            <p v-else class="max-w-[46ch] font-mono text-[0.6rem] text-text-dim">
              Falls back to the badge mark when no photos are set. The product page shows every photo as a
              carousel; ← / → reorder, ✕ removes. Uploaded files are resized, compressed, and committed when you
              hit Publish; picked/typed paths use that file as-is.
            </p>
          </div>

          <div class="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <label class="flex flex-col gap-1">
              <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">SKU</span>
              <input v-model="p.sku" type="text" class="border border-border bg-bg-alt px-3 py-2 font-mono text-sm">
            </label>
            <label class="flex flex-col gap-1">
              <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">Name</span>
              <input :value="p.name" type="text" class="border border-border bg-bg-alt px-3 py-2 font-mono text-sm" @input="onNameInput(p, $event.target.value)">
            </label>
            <label class="flex flex-col gap-1">
              <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">Category</span>
              <select v-model="p.category" class="border border-border bg-bg-alt px-3 py-2 font-mono text-sm">
                <option v-for="c in session.catalog.categories" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </label>
            <label class="flex flex-col gap-1">
              <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">Price (USD)</span>
              <input v-model.number="p.price" type="number" step="0.01" min="0" class="border border-border bg-bg-alt px-3 py-2 font-mono text-sm">
            </label>
            <label class="flex flex-col gap-1">
              <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">Stock</span>
              <input v-model.number="p.stock" type="number" step="1" min="0" class="border border-border bg-bg-alt px-3 py-2 font-mono text-sm">
            </label>
            <label class="flex items-center gap-2">
              <input v-model="p.active" type="checkbox">
              <span class="text-sm">Visible in store</span>
            </label>
            <label class="flex items-center gap-2">
              <input v-model="p.featured" type="checkbox">
              <span class="text-sm">Featured on homepage</span>
            </label>
          </div>

          <label class="mb-4 flex flex-col gap-1">
            <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">Description</span>
            <textarea v-model="p.description" rows="2" class="border border-border bg-bg-alt px-3 py-2 text-sm"></textarea>
          </label>

          <label class="flex flex-col gap-1">
            <span class="font-mono text-[0.65rem] uppercase tracking-wide text-text-dim">Specs (one "Key: Value" per line)</span>
            <textarea v-model="specsDraft[p.id]" rows="3" class="border border-border bg-bg-alt px-3 py-2 font-mono text-sm" @blur="commitSpecs(p)"></textarea>
          </label>
        </div>
      </div>

      <div class="mt-6 flex flex-col gap-3 border-t border-border pt-6">
        <div class="flex flex-wrap items-center gap-3">
          <button
            type="button"
            :disabled="saving"
            class="border border-brand bg-brand px-5 py-3 font-mono text-xs uppercase tracking-wide text-white hover:opacity-90 disabled:opacity-40"
            @click="save"
          >
            Publish changes to GitHub
          </button>
          <span
            class="font-mono text-xs"
            :class="saveStatus.kind === 'ok' ? 'text-text' : saveStatus.kind === 'error' ? 'text-brand' : 'text-text-dim'"
          >
            {{ saveStatus.text }}
          </span>
        </div>
        <SpectrumLoader v-if="saving" class="max-w-xs" />
      </div>
    </div>
  </main>
</template>
