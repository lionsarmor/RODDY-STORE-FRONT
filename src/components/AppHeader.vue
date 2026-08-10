<script setup>
import { useRoute } from "vue-router";
import { useThemeStore } from "../stores/theme";
import { useCartStore } from "../stores/cart";
import { useUiStore } from "../stores/ui";
import RoddyLogo from "./RoddyLogo.vue";

const route = useRoute();
const theme = useThemeStore();
const cart = useCartStore();
const ui = useUiStore();

const navLinks = [
  { label: "Shop", to: "/shop", query: {} },
  { label: "Games", to: "/shop", query: { cat: "games" } },
  { label: "Computers", to: "/shop", query: { cat: "computers" } },
  { label: "Pocket", to: "/shop", query: { cat: "pocket" } },
  { label: "Labs", to: "/shop", query: { cat: "labs" } },
  { label: "Objects", to: "/shop", query: { cat: "objects" } },
  { label: "About", to: "/about", query: {} },
];

// RouterLink's exact-active-class only checks the matched route record, so
// every /shop?cat=* link lights up together — compare the query too.
function isNavLinkActive(link) {
  return route.path === link.to && (route.query.cat || "") === (link.query.cat || "");
}
</script>

<template>
  <header class="sticky top-0 z-40 border-b border-border bg-bg transition-colors duration-200">
    <div class="mx-auto flex max-w-6xl items-center gap-5 px-6 py-3">
      <button
        type="button"
        class="flex flex-shrink-0 items-center gap-2 p-1 glow-hover"
        title="Click to shift RODDY's era"
        @click="theme.cycle()"
      >
        <RoddyLogo kind="full_logo" class="h-8 w-auto" />
        <span class="hidden items-center gap-1 font-mono text-[0.62rem] uppercase tracking-wider text-text-dim sm:flex">
          READY.
          <span class="cursor-blink inline-block h-[0.9em] w-[0.5em] bg-text-dim" />
        </span>
      </button>

      <nav class="flex flex-1 gap-4 overflow-x-auto" style="scrollbar-width: none">
        <RouterLink
          v-for="link in navLinks"
          :key="link.label"
          :to="{ path: link.to, query: link.query }"
          class="whitespace-nowrap border-b-2 border-transparent py-1 font-mono text-xs uppercase tracking-wide text-text-dim transition-colors hover:border-brand hover:text-text"
          :class="isNavLinkActive(link) ? 'border-brand! text-text!' : ''"
        >
          {{ link.label }}
        </RouterLink>
      </nav>

      <div class="flex flex-shrink-0 items-center gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-1 border border-border px-3 py-2 font-mono text-xs uppercase tracking-wide transition-colors hover:bg-accent hover:text-accent-text"
          @click="ui.openThemeOverlay()"
        >
          ◧ Theme
        </button>
        <RouterLink
          to="/cart"
          class="relative inline-flex items-center gap-1 border border-border px-3 py-2 font-mono text-xs uppercase tracking-wide transition-colors hover:bg-accent hover:text-accent-text"
        >
          Cart
          <span
            v-if="cart.count > 0"
            class="inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-brand px-1 font-mono text-[0.65rem] text-white"
          >
            {{ cart.count }}
          </span>
        </RouterLink>
      </div>
    </div>
  </header>
</template>
