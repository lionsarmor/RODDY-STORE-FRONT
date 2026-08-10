<script setup>
import { computed } from "vue";
import { useThemeStore } from "../stores/theme";

const props = defineProps({
  kind: { type: String, default: "full_logo" }, // "full_logo" | "badge"
});

const theme = useThemeStore();
const src = computed(() => theme.logoSrc(props.kind));
</script>

<template>
  <img :src="src" :alt="`RODDY ● — ${theme.current.label} edition`">
</template>
