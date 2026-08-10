<script setup>
import { onMounted } from "vue";
import { useTaglineStore } from "../stores/tagline";

defineProps({
  tag: { type: String, default: "span" },
});

const tagline = useTaglineStore();
onMounted(() => tagline.start());
</script>

<template>
  <Transition name="tagline-fade" mode="out-in">
    <component :is="tag" :key="tagline.current">{{ tagline.current }}</component>
  </Transition>
</template>
