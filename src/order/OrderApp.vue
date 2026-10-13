<script setup>
import { ref, onMounted } from "vue";
import RoddyLogo from "../components/RoddyLogo.vue";
import { useThemeStore } from "../stores/theme";
import { useCatalogStore } from "../stores/catalog";
import { useCartStore } from "../stores/cart";
import { downloadDestination } from "../checkout-links";
useThemeStore();
const catalog = useCatalogStore();
const cart = useCartStore();
// The bearer reference stays in the URL fragment, outside HTTP logs/referrers.
let savedOrder = "";
try {
  savedOrder = sessionStorage.getItem("roddy:last-order") || "";
} catch {}
const sessionId =
  new URLSearchParams(location.hash.slice(1)).get("session_id") || savedOrder;
const state = ref("loading");
const message = ref("");
const downloads = ref([]);
const sandbox = ref(false);
const fulfillments = ref([]);
const orderItems = ref([]);
let cartReconciled = false;
try { cartReconciled = sessionStorage.getItem("roddy:cart-reconciled:" + sessionId) === "1"; } catch {}
async function verify() {
  state.value = "loading";
  downloads.value = [];
  try {
    if (!sessionId)
      throw new Error(
        "No order reference was provided. Contact RODDY with your payment receipt.",
      );
    await catalog.load();
    if (!catalog.settings.checkoutEndpoint)
      throw new Error(
        "We cannot check this order right now. Please contact RODDY with your payment receipt.",
      );
    const res = await fetch(
      catalog.settings.checkoutEndpoint.replace(/\/$/, "") + "/order",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ sessionId }),
      },
    );
    const data = await res.json();
    sandbox.value = data.mode === "sandbox";
    if (!res.ok)
      throw new Error(data.error || "Could not verify your payment.");
    if (data.paid) {
      state.value = "paid";
      downloads.value = (data.downloads || [])
        .map((d) => ({
          ...d,
          url: downloadDestination(d.url, catalog.settings.checkoutEndpoint),
        }))
        .filter((d) => d.url);
      fulfillments.value = data.fulfillments || [];
      orderItems.value = data.items || [];
      if (!cartReconciled) {
        for (const item of orderItems.value) {
          const entry = cart.items.find(i => i.id === item.id && (i.variantId || "") === (item.variantId || ""));
          if (entry) cart.setQty(item.id, entry.qty - item.qty, item.variantId || "");
        }
        cartReconciled = true;
        try { sessionStorage.setItem("roddy:cart-reconciled:" + sessionId, "1"); } catch {}
      }
      try {
        sessionStorage.removeItem("roddy:checkout-attempt");
      } catch {}
    } else {
      state.value = "pending";
      message.value =
        "Your payment has not been confirmed yet. Check again shortly, or refer to your payment receipt.";
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
      <p v-if="sandbox" class="notice my-4">Test order — no money charged. The download contains a test file.</p>
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
            ? "Your payment is confirmed. Downloads and shipment updates are shown below."
            : message
        }}
      </p>
      <div v-if="state === 'paid'" class="my-6 space-y-4">
        <a
          v-for="file in downloads"
          :key="file.url"
          :href="file.url"
          class="button primary"
          rel="noreferrer"
          >↓ Download {{ file.name }}</a
        >
        <section v-for="f in fulfillments" :key="f.kind" class="border border-border p-4 text-left">
          <h2 class="font-bold">{{f.kind === 'office' ? 'Ships from RODDY' : 'Made to order'}} · {{f.state.replaceAll('-', ' ')}}</h2>
          <p v-for="s in f.shipments" :key="s.number" class="mt-3 text-sm">{{s.carrier}} · {{s.number}} <a v-if="/^https?:\/\//.test(s.url || '')" :href="s.url" target="_blank" rel="noopener noreferrer" class="text-button">Track shipment ↗</a></p>
          <p v-if="f.state === 'review'" class="mt-3 text-sm">RODDY is reviewing fulfillment. Your payment is confirmed.</p>
        </section>
        <p v-if="orderItems.some(i => i.kind !== 'digital')" class="text-sm">Items may arrive in separate shipments. Check this page for updates.</p>
        <p class="text-xs leading-relaxed text-text-dim">
          Follow the instructions inside your download. Download links last 15
          minutes; check order status again to refresh them. Bookmark this
          page privately to return to your order for 30 days.
        </p>
        <p v-if="!downloads.length && orderItems.some(i => i.kind === 'digital')" class="release-note">
          Your download is unavailable. Please contact RODDY with your receipt.
        </p>
      </div>
      <p v-if="sessionId" class="my-6 break-all font-mono text-xs">
        REF {{ sessionId.slice(-12).toUpperCase() }}
      </p>
      <button v-if="state !== 'loading'" class="button mb-4" @click="verify">
        Check order status ↻</button
      ><a href="./index.html#/shop" class="button primary"
        >Back to the catalog ↗</a
      >
    </div>
  </main>
</template>
