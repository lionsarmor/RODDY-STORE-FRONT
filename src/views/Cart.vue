<script setup>
import { computed, ref, reactive, watch, onMounted } from "vue";
import { useRoute } from "vue-router";
import {
  useCatalogStore,
  formatPrice,
  productImageUrl,
  stockState,
} from "../stores/catalog";
import { useCartStore } from "../stores/cart";
import { useCheckoutStore } from "../stores/checkout";
import { useUiStore } from "../stores/ui";
import { estimateShipping, variantLabel, cartLineKey } from "../merch.js";
import { shippingCountries } from '../shipping-destinations.js';
import {profileFor,designError,designLabel} from '../keycaps.js';
import {useCustomerStore} from '../stores/customer';
import {emptyAddress} from '../customer-api';
import AddressFields from '../components/AddressFields.vue';
const address = reactive({first_name: "", last_name: "", email: "", phone: "", country: "US", region: "", address1: "", address2: "", city: "", zip: ""});
const destination = computed(() => address.country);
const quote = ref(null);
function quotedPrice(item){return (quote.value?.items?.find(i=>i.id===item.id && i.variantId===(item.variantId || ''))?.unitPriceCents ?? item.price*100)/100;}
const quoting = ref(false);
const quoteError = ref("");
const route = useRoute();
const customer = useCustomerStore();
const guestMode = ref(route.query.guest === '1');
const savedAddressId = ref('');
const saveForLater = ref(false);
const addressLabel = ref('Home');
const accountMessage = ref('');
const catalog = useCatalogStore();
const cart = useCartStore();
const checkout = useCheckoutStore();
const ui = useUiStore();
async function loadCustomer() {
  if (!catalog.settings.checkoutEndpoint) return;
  try {
    await customer.load();
    if (!guestMode.value && JSON.stringify(address)===JSON.stringify(emptyAddress())) {
      const saved=customer.addresses.find(a=>a.default);
      if(saved){savedAddressId.value=saved.id;Object.assign(address,saved.address);}
    }
  } catch {accountMessage.value='Saved addresses could not load. You can enter an address and check out as a guest.';}
}
function chooseAddress() {
  const saved=customer.addresses.find(a=>a.id===savedAddressId.value);
  Object.assign(address,saved ? saved.address : {...emptyAddress(),email:customer.profile?.email || ''});
  saveForLater.value=false;
}
function useGuest() {
  guestMode.value=true;saveForLater.value=false;savedAddressId.value='';
  Object.assign(address,emptyAddress());accountMessage.value='Guest checkout selected. This address will only be used for this order.';
}
onMounted(loadCustomer);
watch(()=>catalog.settings.checkoutEndpoint,loadCustomer);
watch(()=>route.query.guest,value=>{if(value==='1')useGuest();});
watch(()=>customer.session?.token,(token,previous)=>{
  if(previous && token!==previous && savedAddressId.value){
    savedAddressId.value='';saveForLater.value=false;Object.assign(address,emptyAddress());
    accountMessage.value='Your account changed. Choose or enter a delivery address again.';
  }
});
const items = computed(() => cart.hydrated(catalog));
const missing = computed(() => cart.items.filter((i) => !catalog.byId(i.id)));
const total = computed(() =>
  items.value.reduce((sum, i) => sum + i.price * i.qty, 0),
);
const physical = computed(() =>
  items.value.some((i) => i.product.type !== "digital"),
);
const shipping = computed(() =>
  physical.value ? estimateShipping(items.value, destination.value) : 0,
);
function itemError(item) {
  if (item.product.type === 'physical' && !shippingCountries(item.product).includes(destination.value)) return 'This item does not ship to the selected country. Choose another destination or remove it.';
  if (["soon", "out"].includes(stockState(item.product)) || item.product.pricePending) return 'This item is not available to buy.';
  if (item.product.keycaps) {
    const error = designError(item.design, profileFor(catalog, item.product));
    if (error) return error;
    if (["soon", "out"].includes(stockState(item.product)) || item.product.pricePending) return "This set is temporarily unavailable.";
    return "";
  }
  if (item.product.merch) {
    if (!item.variant || !item.variant.enabled) return "This selection is no longer offered. Choose a color and size on the product page.";
    if (item.variant.available !== true) return "This selection is unavailable. Choose another color or size.";
    return "";
  }
  if (item.product.price <= 0) return "Get free downloads from their product pages.";
  if (item.product.type === "digital" && item.qty !== 1) return "Choose one copy of this digital download.";
  if (item.product.type === "physical" && !item.product.trackStock && !["manual","automatic"].includes(item.product.supplier?.fulfillment || item.product.fulfillment)) return "This item is temporarily unavailable.";
  if (
    ["soon", "out"].includes(stockState(item.product)) ||
    item.product.pricePending
  )
    return "This item is not available to buy.";
  if (item.product.trackStock && item.qty > item.product.stock)
    return `Only ${item.product.stock} available. Reduce the quantity.`;
  return "";
}
const invalid = computed(
  () => missing.value.length > 0 || items.value.some(itemError),
);
watch(() => JSON.stringify([cart.items, address]), () => { quote.value = null; quoteError.value = ""; });
async function getQuote() {
  quoting.value = true; quoteError.value = ""; quote.value = null;
  const fingerprint = JSON.stringify([cart.items, address]);
  try {
    const res = await fetch(catalog.settings.checkoutEndpoint.replace(/\/$/, "") + "/quote", {
      method: "POST", headers: {"content-type": "application/json"}, body: JSON.stringify({items: cart.items, address})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not calculate shipping.");
    if (fingerprint === JSON.stringify([cart.items, address])) {
      quote.value = data;
      if(customer.signedIn && !guestMode.value && saveForLater.value) {
        try {
          savedAddressId.value=await customer.saveAddress({label:addressLabel.value,address:{...address},default:!customer.addresses.length});
          saveForLater.value=false;accountMessage.value='Address saved to your account.';
        } catch(e) {accountMessage.value='Shipping is ready, but your address was not saved: '+e.message;}
      }
    }
  } catch (e) { quoteError.value = e.message; }
  finally { quoting.value = false; }
}
async function checkoutAll() {
  if (invalid.value || (physical.value && !quote.value)) return;
  try {
    await checkout.checkout(cart.items, physical.value ? quote.value?.quoteId : "");
  } catch (e) {
    ui.toast(e.message);
  }
}
function updateQty(item, value) {
  cart.setQty(
    item.product.id,
    Math.min(
      item.product.type === "digital" ? 1 : 99,
      Math.max(1, Math.trunc(Number(value)) || 1),
    ),
    item.variantId || "",
    item.design,
  );
}
</script>
<template>
  <div class="mx-auto max-w-6xl px-6 py-12">
    <p class="eyebrow">RODDY / YOUR NEXT BIG IDEA</p>
    <h1 class="mb-8 mt-3 text-4xl font-extrabold tracking-tight">YOUR CART.</h1>
    <p v-if="route.query.canceled" class="notice mb-6">
      Checkout was canceled. Your cart is still here.
    </p>
    <div v-if="!catalog.loaded" class="empty-state">Loading your cart…</div>
    <div v-else-if="!cart.items.length" class="empty-state">
      Your cart is empty.
      <RouterLink to="/shop" class="text-button"
        >Explore the catalog ↗</RouterLink
      >
    </div>
    <div v-else class="grid gap-8 lg:grid-cols-[1.5fr_1fr]">
      <div>
        <div v-for="entry in missing" :key="cartLineKey(entry.id, entry.variantId, entry.design)" class="notice mb-4">
          An item is no longer in the catalog: {{ entry.id }}.
          <button class="text-button" @click="cart.remove(entry.id, entry.variantId, entry.design)">
            Remove
          </button>
        </div>
        <div
          v-for="item in items"
          :key="item.key"
          class="mb-4 flex flex-wrap items-center gap-5 border border-border bg-panel p-5"
        >
          <img
            v-if="item.product.coverImage || item.product.images[0]"
            :src="
              productImageUrl(item.variant?.image || item.product.coverImage || item.product.images[0])
            "
            :alt="item.product.name"
            class="h-20 w-20 object-cover"
          />
          <div class="min-w-0 flex-1">
            <RouterLink
              :to="`/product/${item.product.id}`"
              class="font-mono text-sm font-bold"
              >{{ item.product.name }}</RouterLink
            >
            <p v-if="item.design" class="mt-2 text-xs leading-relaxed">{{designLabel(item.design)}}</p>
            <p v-if="item.variant" class="mt-2 text-sm">{{ variantLabel(item.variant) }}</p>
            <p class="mt-2 font-mono text-xs text-text-dim">
              {{
                item.product.pricePending
                  ? "Pricing TBA"
                  : formatPrice(quotedPrice(item)) + " each"
              }}
              · {{ item.product.type }}
            </p>
            <p v-if="itemError(item)" class="mt-3 text-xs text-brand">
              {{ itemError(item) }}
            </p>
          </div>
          <label class="quantity-field"
            >Quantity<input
              :value="item.qty"
              type="number"
              min="1"
              :max="
                item.product.type === 'digital'
                  ? 1
                  : item.product.trackStock
                    ? Math.min(99, item.product.stock)
                    : 99
              "
              @change="updateQty(item, $event.target.value)"
          /></label>
          <button class="text-button" @click="cart.remove(item.product.id, item.variantId, item.design)">
            Remove
          </button>
        </div>
        <RouterLink to="/shop" class="text-button">← Keep exploring</RouterLink>
      </div>
      <section class="self-start border border-border bg-panel p-6">
        <h2 class="mb-6 font-mono text-base">ORDER SUMMARY</h2>
        <div class="checkout-account">
          <template v-if="customer.signedIn && !guestMode"><p>Shopping as <strong>{{customer.profile.handle}}</strong></p><RouterLink to="/account?return=cart" class="text-button">Manage account</RouterLink> · <button class="text-button" @click="useGuest">Use guest checkout</button></template>
          <template v-else><p><strong>Guest checkout.</strong> No account needed.</p><RouterLink to="/account?return=cart" class="text-button">Sign in or create an account</RouterLink><button v-if="customer.signedIn" class="text-button" @click="guestMode=false;accountMessage=''">Use my saved addresses</button></template>
          <p v-if="accountMessage" class="text-xs mt-2" role="status">{{accountMessage}}</p>
        </div>
        <div class="mb-4 flex justify-between text-sm">
          <span>Subtotal</span><span>{{ formatPrice(quote ? quote.subtotal/100 : total) }}</span>
        </div>
        <form v-if="physical" class="shipping-form mb-6" @submit.prevent="getQuote">
          <h3 class="font-mono mb-4">DELIVERY ADDRESS</h3>
          <label v-if="customer.signedIn && !guestMode && customer.addresses.length" class="saved-address-picker">Use a saved address<select v-model="savedAddressId" @change="chooseAddress"><option value="">Enter another address</option><option v-for="saved in customer.addresses" :key="saved.id" :value="saved.id">{{saved.label}} — {{saved.address.city}}{{saved.default?' (default)':''}}</option></select></label>
          <AddressFields :address="address" />
          <div v-if="customer.signedIn && !guestMode && customer.addresses.length<10" class="save-address-choice"><label><input v-model="saveForLater" type="checkbox" /> Save this as a new address for next time</label><label v-if="saveForLater">Address label<input v-model="addressLabel" maxlength="40" required placeholder="Home, work…" /></label></div>
          <button class="button w-full mt-4" type="submit" :disabled="quoting || invalid || catalog.preview">{{ quoting ? 'Calculating…' : 'Update prices & shipping' }}</button>
          <p v-if="quoteError" class="release-note" role="alert">{{ quoteError }}</p>
          <p v-if="quote" class="text-xs mt-3">Prices and shipping confirmed for this address. Review the total before paying. Quote expires after 15 minutes; availability is rechecked at checkout.</p>
        </form>
        <div class="mb-4 flex justify-between text-sm">
          <span>{{
            physical ? (quote ? "Standard shipping" : "Shipping estimate") : "Shipping"
          }}</span
          ><span>{{
            physical
              ? quote ? formatPrice(quote.shipping / 100) : shipping === null ? "Calculate above" : formatPrice(shipping)
              : "Not required"
          }}</span>
        </div>
        <div
          class="mb-5 flex justify-between border-t border-border pt-4 font-mono text-lg"
        >
          <span>{{quote?'Total to pay':'Estimated total'}}</span
          ><span>{{ formatPrice(quote ? quote.amountTotal / 100 : total + (shipping || 0)) }}{{ physical && !quote ? " (estimate)" : "" }}</span>
        </div>
        <p class="mb-5 text-xs leading-relaxed text-text-dim">
          {{ physical ? "USD. One payment covers your order. Downloads unlock after payment. Items may arrive in separate packages." : "USD. Your software download appears after payment is confirmed." }}
        </p>
        <button
          class="button primary w-full"
          :disabled="
            checkout.loading ||
            invalid ||
            (physical && !quote) ||
            !catalog.settings.checkoutEnabled ||
            catalog.preview
          "
          @click="checkoutAll"
        >
          {{ checkout.loading ? "Opening checkout…" : customer.signedIn && !guestMode ? "Secure checkout ↗" : "Checkout as guest ↗" }}
        </button>
        <p v-if="!catalog.settings.checkoutEnabled" class="release-note">
          Checkout is getting ready. Your cart is saved on this device.
        </p>
        <p v-if="invalid" class="release-note">
          Update the unavailable items above to continue.
        </p>
        <p class="mt-4 text-center font-mono text-[9px] text-text-dim">
          SECURE PAYMENTS BY SQUARE
        </p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.checkout-account{padding:16px;border:1px solid var(--color-border);border-radius:8px;margin-bottom:24px;font-size:13px;line-height:1.7}.saved-address-picker{display:grid;gap:8px;font-size:13px;margin-bottom:20px}.saved-address-picker select,.save-address-choice input:not([type=checkbox]){width:100%;min-width:0;padding:10px;background:var(--color-panel);border:1px solid var(--color-border);color:inherit}.save-address-choice{display:grid;gap:10px;font-size:12px;margin-top:16px}.save-address-choice label{display:flex;gap:8px;align-items:center}
.shipping-fields { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
.shipping-fields label { display:grid; gap:6px; min-width:0; font-size:12px; }
.shipping-fields .wide { grid-column:1/-1; }
.shipping-fields input, .shipping-fields select { width:100%; min-width:0; background:var(--color-panel, #101115); color:inherit; border:1px solid var(--color-border, #444); padding:10px; font:inherit; }
</style>
