<script setup>
import { computed } from "vue";
import { useThemeStore } from "../stores/theme";
import fullOutline from "../../public/img/logos/RODDY_SVG_BRAND_PACK/full_logo/outline/roddy_full_classic_cream_red_outline.svg?raw";
import badgeOutline from "../../public/img/logos/RODDY_SVG_BRAND_PACK/badge/outline/roddy_badge_classic_cream_red_outline.svg?raw";

const props = defineProps({
  kind: { type: String, default: "full_logo" }, // "full_logo" | "badge"
  onAccent: { type: Boolean, default: false },
});

const theme = useThemeStore();
// Trusted, bundled brand-pack vectors: preserve the original outline, letter
// shapes and dot. Only palette colors and the badge's padded artboard change.
function paths(source) {
  return source.match(/<g[\s\S]*<\/g>/)[0]
    .replace(/ id="[^"]*"/g, "")
    .replaceAll('fill="#000000"', 'fill="currentColor"')
    .replaceAll('fill="#C32D28"', 'fill="var(--logo-dot)"');
}
const artwork = { full_logo: paths(fullOutline), badge: paths(badgeOutline) };
const isBadge = computed(() => props.kind === "badge");
const colors = computed(() => ({
  color: props.onAccent ? "var(--color-accent-text)" : theme.current.swatch[1],
  "--logo-dot": theme.currentId === "collector-gold"
    ? "#c32d28"
    : theme.current.swatch[2],
}));
</script>

<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="isBadge ? '441 273 532 291' : '233.5 263.6 1012.2 285.4'"
    :style="colors"
    role="img"
    :aria-label="`RODDY ● — ${theme.current.label} edition`"
    :data-logo="isBadge ? 'badge' : 'full_logo'"
    class="roddy-logo"
    v-html="artwork[isBadge ? 'badge' : 'full_logo']"
  />
</template>
