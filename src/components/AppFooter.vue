<script setup>
import { useThemeStore } from "../stores/theme";
import RoddyLogo from "./RoddyLogo.vue";
import RotatingTagline from "./RotatingTagline.vue";

const theme = useThemeStore();
</script>

<template>
  <footer class="mt-auto border-t border-border py-10 transition-colors duration-200">
    <div class="mx-auto max-w-6xl px-6">
      <div class="grid grid-cols-1 gap-8 sm:grid-cols-[2fr_1fr_1fr]">
        <div>
          <RoddyLogo kind="full_logo" class="h-7 w-auto" />
          <p class="mt-3 max-w-[32ch] text-sm text-text-dim">
            <RotatingTagline tag="span" /> Currently running the
            <strong class="text-text">{{ theme.current.label }}</strong> edition — click the logo to shift eras.
          </p>
        </div>
        <div>
          <h4 class="mb-3 font-mono text-[0.7rem] uppercase tracking-wide text-text-dim">Shop</h4>
          <RouterLink
            v-for="cat in ['games', 'computers', 'pocket', 'labs', 'objects']"
            :key="cat"
            :to="{ path: '/shop', query: { cat } }"
            class="mb-2 block font-mono text-sm capitalize hover:text-brand"
          >
            {{ cat }}
          </RouterLink>
        </div>
        <div>
          <h4 class="mb-3 font-mono text-[0.7rem] uppercase tracking-wide text-text-dim">Company</h4>
          <RouterLink to="/about" class="mb-2 block font-mono text-sm hover:text-brand">Brand map</RouterLink>
          <RouterLink to="/cart" class="mb-2 block font-mono text-sm hover:text-brand">Cart</RouterLink>
          <span class="block font-mono text-sm">PLAY · BUILD · PROGRAM · KEEP</span>
        </div>
      </div>
      <div class="mt-8 flex flex-wrap justify-between gap-2 border-t border-border pt-5 font-mono text-[0.68rem] tracking-wide text-text-dim">
        <span>RODDY ● — established alternate 1983</span>
        <span>Every purchase is processed securely via Stripe.</span>
      </div>
    </div>
  </footer>
</template>
