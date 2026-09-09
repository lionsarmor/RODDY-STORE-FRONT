<script setup>
import { ref, onBeforeUnmount } from "vue";
import { compressImage } from "./image";
import { productImageUrl } from "../stores/catalog";
const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  single: Boolean,
  library: { type: Array, default: () => [] },
  title: { type: String, default: "Images" },
});
const emit = defineEmits(["update:modelValue", "busy"]);
const busy = ref(false);
const error = ref("");
const url = ref("");
const dragging = ref(false);
let disposed = false;
onBeforeUnmount(() => {
  disposed = true;
  if (busy.value) emit("busy", false);
});
function add(paths) {
  emit(
    "update:modelValue",
    props.single ? paths.slice(-1) : [...props.modelValue, ...paths],
  );
}
async function upload(files) {
  if (busy.value) return;
  busy.value = true;
  emit("busy", true);
  error.value = "";
  try {
    const sources = [];
    for (const file of Array.from(files).slice(0, props.single ? 1 : 20)) {
      if (!/^image\/(jpeg|png|webp|gif)$/.test(file.type))
        throw new Error("Choose JPG, PNG, WebP or GIF images.");
      if (file.size > 20 * 1024 * 1024)
        throw new Error("Each image must be under 20 MB.");
      sources.push(await compressImage(file, { maxDim: 1600 }));
    }
    if (sources.length && !disposed) add(sources);
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
    if (!disposed) emit("busy", false);
  }
}
function move(i, direction) {
  const next = [...props.modelValue];
  const target = i + direction;
  if (target < 0 || target >= next.length) return;
  [next[i], next[target]] = [next[target], next[i]];
  emit("update:modelValue", next);
}
function remove(i) {
  emit(
    "update:modelValue",
    props.modelValue.filter((_, n) => i !== n),
  );
}
function addUrl() {
  if (
    !/^https:\/\//.test(url.value) &&
    !/^img\/[a-zA-Z0-9_./ -]+$/.test(url.value)
  ) {
    error.value = "Use an HTTPS image URL or an img/ path.";
    return;
  }
  add([url.value.trim()]);
  url.value = "";
  error.value = "";
}
</script>
<template>
  <section class="media-editor">
    <div class="field-heading">
      <h3>{{ title }}</h3>
      <span>{{ modelValue.length }} {{ single ? "/ 1" : "images" }}</span>
    </div>
    <label
      class="upload-zone"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="
        dragging = false;
        upload($event.dataTransfer.files);
      "
    >
      <span>{{
        busy ? "Preparing images…" : "↑ Drop images here or choose files"
      }}</span
      ><small
        >JPG, PNG, WebP or GIF · up to 20 MB each · optimized to JPG</small
      >
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        :multiple="!single"
        :disabled="busy"
        @change="
          upload($event.target.files);
          $event.target.value = '';
        "
      />
    </label>
    <div v-if="modelValue.length" class="media-grid">
      <div v-for="(src, i) in modelValue" :key="i" class="media-tile">
        <img :src="productImageUrl(src)" :alt="`${title} ${i + 1}`" /><span
          v-if="src.startsWith('data:')"
          class="media-pending"
          >DRAFT</span
        >
        <div>
          <button
            v-if="!single"
            :disabled="i === 0"
            :aria-label="`Move image ${i + 1} earlier`"
            @click="move(i, -1)"
          >
            ←</button
          ><span>{{ i + 1 }}</span
          ><button
            v-if="!single"
            :disabled="i === modelValue.length - 1"
            :aria-label="`Move image ${i + 1} later`"
            @click="move(i, 1)"
          >
            →</button
          ><button :aria-label="`Remove image ${i + 1}`" @click="remove(i)">
            ×
          </button>
        </div>
      </div>
    </div>
    <div class="media-url">
      <input
        v-model="url"
        :aria-label="`${title} URL`"
        placeholder="https://… or img/products/…"
        @keydown.enter.prevent="addUrl"
      /><button class="button small" :disabled="!url" @click="addUrl">
        Add
      </button>
    </div>
    <label v-if="library.length"
      >Choose from uploaded images<select
        @change="
          add([$event.target.value]);
          $event.target.value = '';
        "
      >
        <option value="">Select existing image…</option>
        <option v-for="path in library" :key="path" :value="path">
          {{ path }}
        </option>
      </select></label
    >
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
  </section>
</template>
