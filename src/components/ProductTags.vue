<script setup>
import { computed } from "vue";
import { useCatalogStore } from "../stores/catalog";
const props = defineProps({
  ids: { type: Array, default: () => [] },
  definitions: Array,
});
const catalog = useCatalogStore();
const tags = computed(() =>
  props.ids
    .map((id) => (props.definitions || catalog.tags).find((t) => t.id === id))
    .filter(Boolean),
);
function ink(hex) {
  const rgb = (hex.match(/[a-f0-9]{2}/gi) || ["ff", "ff", "ff"]).map((v) =>
    parseInt(v, 16),
  );
  return rgb[0] * 0.299 + rgb[1] * 0.587 + rgb[2] * 0.114 > 150
    ? "#171717"
    : "#ffffff";
}
</script>
<template>
  <div v-if="tags.length" class="product-tags">
    <span
      v-for="tag in tags"
      :key="tag.id"
      class="tag-pill"
      :style="{ backgroundColor: tag.color, color: ink(tag.color) }"
      >{{ tag.label }}</span
    >
  </div>
</template>
