<script setup>
import { ref, onMounted } from "vue";
import RoddyLogo from "../components/RoddyLogo.vue";
import { useThemeStore } from "../stores/theme";
import { useCatalogStore } from "../stores/catalog";
import { useCartStore } from "../stores/cart";
useThemeStore();
const catalog = useCatalogStore();
const cart = useCartStore();
const sessionId = new URLSearchParams(location.search).get("session_id") || "";
const state = ref("loading");
const message = ref("");
async function verify() {
  state.value = "loading";
  try {
    if (!sessionId)
      throw new Error(
        "No order reference was provided. Check your Stripe receipt for confirmation.",
      );
    await catalog.load();
    if (!catalog.settings.checkoutEndpoint)
      throw new Error(
        "We cannot check this order right now. Please check your Stripe receipt or contact RODDY.",
      );
    const res = await fetch(
      catalog.settings.checkoutEndpoint.replace(/\/$/, "") +
        "/order?session_id=" +
        encodeURIComponent(sessionId),
    );
    const data = await res.json();
    if (!res.ok)
      throw new Error(data.error || "Could not verify your payment.");
    if (data.paid) {
      state.value = "paid";
      cart.clear();
    } else {
      state.value = "pending";
      message.value =
        "Your payment has not been confirmed yet. Check again shortly, or refer to your Stripe receipt.";
    }
  } catch (e) {
    state.value = "unverified";
    message.value = e.message;
  }
}
onMounted(verify);
</script>
<template>
  <header class="border-b border-border p-6">
    <a href="./index.html"
      ><RoddyLogo kind="full_logo" class="mx-auto h-8 w-auto"
    /></a>
  </header>
  <main class="mx-auto max-w-xl px-6 py-20 text-center">
    <div class="border border-border bg-panel p-8">
      <p class="mb-5 text-4xl text-brand">{{ state === "paid" ? "✓" : "●" }}</p>
      <p class="eyebrow">RODDY / ORDER DESK</p>
      <h1 class="my-5 text-3xl font-extrabold tracking-tight">
        {{
          state === "paid"
            ? "YOU’RE IN. THANK YOU."
            : state === "loading"
              ? "CHECKING YOUR ORDER…"
              : "LET’S CHECK YOUR ORDER."
        }}
      </h1>
      <p class="text-sm leading-relaxed text-text-dim">
        {{
          state === "paid"
            ? "Stripe has confirmed your order. Thanks for bringing a little more RODDY into your world."
            : message
        }}
      </p>
      <p v-if="sessionId" class="my-6 break-all font-mono text-xs">
        REF {{ sessionId.slice(-12).toUpperCase() }}
      </p>
      <button
        v-if="state === 'pending' || state === 'unverified'"
        class="button mb-4"
        @click="verify"
      >
        Check payment status ↻</button
      ><a href="./index.html#/shop" class="button primary"
        >Back to the catalog ↗</a
      >
    </div>
  </main>
</template>
