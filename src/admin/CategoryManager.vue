<script setup>
import { ref } from 'vue';
import { categoryPreviewUrl } from '../category-visibility.js';
import { slugify } from './utils';
const props = defineProps({ catalog: { type: Object, required: true } });
const message = ref('');
const error = ref('');
const key = () => crypto.randomUUID().replaceAll('-', '');
const link = c => categoryPreviewUrl(window.location.href, c);
function add() {
  let id = 'new-category', n = 2;
  while (props.catalog.categories.some(c => c.id === id)) id = 'new-category-' + n++;
  props.catalog.categories.push({ id, name: 'New category', code: '', visible: false, previewKey: key() });
  message.value = 'New category added as unlisted. Name it, assign products, then publish your changes.';
}
function visibility(c, checked) {
  c.visible = checked;
  if (!checked && !c.previewKey) c.previewKey = key();
  message.value = checked ? 'This category and its active products will be public after publishing.' : 'This category and its products will be unlisted after publishing.';
}
function rename(c, value) {
  const id = slugify(value), old = c.id;
  if (!id || props.catalog.categories.some(other => other !== c && other.id === id)) {
    error.value = 'Use a nonempty, unique category ID.'; return;
  }
  c.id = id;
  for (const p of props.catalog.products) if (p.category === old) p.category = id;
  error.value = '';
}
function move(i, direction) {
  const list = props.catalog.categories, target = i + direction;
  if (target >= 0 && target < list.length) [list[i], list[target]] = [list[target], list[i]];
}
function remove(c) {
  if (props.catalog.products.some(p => p.category === c.id)) {
    error.value = 'Move this category’s products elsewhere before deleting it. You can switch off public visibility instead.'; return;
  }
  props.catalog.categories = props.catalog.categories.filter(other => other !== c);
  error.value = '';
}
async function copy(c) {
  try { await navigator.clipboard.writeText(link(c)); message.value = 'Preview link copied. Publish any pending changes before sharing it.'; }
  catch { message.value = 'Select and copy the preview link below. Publish any pending changes before sharing it.'; }
}
function reset(c) {
  c.previewKey = key();
  message.value = 'New preview link created. Publishing will stop the old link from opening this unlisted category.';
}
</script>
<template>
  <div class="category-manager">
    <div class="section-heading">
      <p class="help-copy">Create categories and arrange the Shop tabs. Turn off public visibility to hide a category and all its products from public browsing and ordinary product links. Publish changes to apply them.</p>
      <button class="button primary small" @click="add">Add category +</button>
    </div>
    <p v-if="message" class="notice" role="status">{{ message }}</p>
    <p v-if="error" class="notice form-error" role="alert">{{ error }}</p>
    <section v-for="(c, i) in catalog.categories" :key="c.previewKey || c.id" class="admin-section" :aria-label="c.name + ' category'">
      <div class="category-row">
        <span class="category-index">{{ String(i + 1).padStart(2, '0') }}</span>
        <label>Name<input v-model="c.name" /></label>
        <label>ID<input :value="c.id" @change="rename(c, $event.target.value)" /></label>
        <label>Caption<input v-model="c.code" /></label>
        <span class="help-copy">{{ catalog.products.filter(p => p.category === c.id).length }} products</span>
        <div class="admin-actions">
          <button class="button small" :disabled="i === 0" aria-label="Move category up" @click="move(i, -1)">↑</button>
          <button class="button small" :disabled="i === catalog.categories.length - 1" aria-label="Move category down" @click="move(i, 1)">↓</button>
          <button class="button small" @click="remove(c)">Delete</button>
        </div>
      </div>
      <label class="check"><input type="checkbox" :checked="c.visible !== false" @change="visibility(c, $event.target.checked)" />Public visibility — {{ c.visible === false ? 'off (unlisted)' : 'on' }}</label>
      <div v-if="c.visible === false" class="category-sharing">
        <p class="help-copy">Anyone with this link can browse this category and its active products. This is an unlisted preview, not password protection. Product availability and checkout checks still apply.</p>
        <label>Unlisted preview link<input :value="link(c)" readonly @focus="$event.target.select()" /></label>
        <div class="admin-actions">
          <button class="button small" @click="copy(c)">Copy preview link</button>
          <a class="button small" :href="link(c)" target="_blank" rel="noopener">Open published preview ↗</a>
          <button class="text-button" @click="reset(c)">Reset preview link</button>
        </div>
      </div>
    </section>
  </div>
</template>
