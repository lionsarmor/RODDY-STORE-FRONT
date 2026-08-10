<script setup>
import { computed } from "vue";
import RoddyLogo from "../components/RoddyLogo.vue";
import { useThemeStore } from "../stores/theme";

useThemeStore(); // ensures the store (and its CSS-var side effects) is active

const params = new URLSearchParams(location.search);
const ref = params.get("session_id") || params.get("ref");
const refText = computed(() => (ref ? `REF ${ref.slice(-12).toUpperCase()}` : "REF — see email receipt"));
</script>

<template>
  <header class="border-b border-border bg-bg transition-colors duration-200">
    <div class="mx-auto flex max-w-6xl items-center gap-5 px-6 py-3">
      <a href="./index.html" class="flex items-center gap-2">
        <RoddyLogo kind="full_logo" class="h-8 w-auto" />
      </a>
      <nav class="flex gap-4">
        <a href="./index.html#/shop" class="font-mono text-xs uppercase tracking-wide text-text-dim hover:text-text">Shop</a>
        <a href="./index.html#/about" class="font-mono text-xs uppercase tracking-wide text-text-dim hover:text-text">About</a>
      </nav>
    </div>
  </header>

  <main class="mx-auto max-w-lg px-6 py-20 text-center">
    <div class="border border-border p-10">
      <p class="mb-3 text-3xl text-brand">●</p>
      <h1 class="mb-3 font-mono text-2xl uppercase tracking-wide">Order confirmed</h1>
      <p class="mb-5 text-text-dim">
        Your order went through Stripe's secure checkout. A receipt is on its way to your inbox — that email is
        your official confirmation.
      </p>
      <code class="mb-6 inline-block border border-dashed border-border px-4 py-2 font-mono">{{ refText }}</code>
      <p>
        <a
          href="./index.html#/shop"
          class="inline-block border border-border px-5 py-3 font-mono text-xs uppercase tracking-wide hover:bg-bg-alt"
        >
          Back to the catalog →
        </a>
      </p>
    </div>
  </main>
  <div class="crt-scanlines" />
</template>
