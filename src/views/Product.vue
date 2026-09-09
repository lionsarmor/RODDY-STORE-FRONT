<script setup>
import { computed, ref, watch } from "vue";
import {
  useCatalogStore,
  stockState,
  stockLabel,
  formatPrice,
  productImageUrl,
} from "../stores/catalog";
import { safeLink } from "../catalog-model.js";
import { useCartStore } from "../stores/cart";
import { useUiStore } from "../stores/ui";
import { useCheckoutStore } from "../stores/checkout";
import ProductTags from "../components/ProductTags.vue";
import ProductArtwork from "../components/ProductArtwork.vue";
const props = defineProps({ id: { type: String, required: true } });
const catalog = useCatalogStore();
const cart = useCartStore();
const ui = useUiStore();
const checkout = useCheckoutStore();
const product = computed(() => catalog.byId(props.id));
const state = computed(() =>
  product.value ? stockState(product.value) : "out",
);
const qty = ref(1);
const activeIndex = ref(0);
const lightbox = ref(null);
const images = computed(() => [
  ...new Set([
    ...(product.value?.images || []),
    ...(!product.value?.images?.length && product.value?.coverImage
      ? [product.value.coverImage]
      : []),
  ]),
]);
const purchasable = computed(
  () =>
    product.value &&
    ["in", "low"].includes(state.value) &&
    !product.value.pricePending,
);
const freeDownload = computed(
  () =>
    purchasable.value &&
    product.value.price === 0 &&
    safeLink(product.value.downloadUrl),
);
const githubLink = computed(() => safeLink(product.value?.githubUrl));
const maxQty = computed(() =>
  product.value?.trackStock ? Math.min(99, product.value.stock) : 99,
);
watch(
  () => props.id,
  () => {
    activeIndex.value = 0;
    qty.value = 1;
  },
);
function move(dir) {
  if (images.value.length)
    activeIndex.value =
      (activeIndex.value + dir + images.value.length) % images.value.length;
}
function quantity() {
  return Math.min(
    maxQty.value,
    Math.max(1, Math.trunc(Number(qty.value)) || 1),
  );
}
function addToCart() {
  if (!purchasable.value) return;
  cart.add(product.value.id, quantity());
  ui.toast(`Added ${product.value.name} to cart`);
}
async function buyNow() {
  try {
    await checkout.checkout([{ id: product.value.id, qty: quantity() }]);
  } catch (e) {
    ui.toast(e.message);
  }
}
</script>
<template>
  <div v-if="!catalog.loaded" class="empty-state">
    {{ catalog.error || "Loading the product…" }}
  </div>
  <div v-else-if="!product" class="empty-state">
    Product not found.
    <RouterLink to="/shop" class="text-button">Back to catalog ↗</RouterLink>
  </div>
  <div v-else class="product-page">
    <nav class="product-breadcrumb" aria-label="Breadcrumb">
      <RouterLink to="/shop">Catalog</RouterLink><span>/</span
      ><RouterLink :to="{ path: '/shop', query: { cat: product.category } }">{{
        catalog.categoryMeta(product.category)?.name
      }}</RouterLink
      ><span>/</span><span>{{ product.name }}</span>
    </nav>
    <div class="product-detail-grid">
      <div>
        <div class="detail-image">
          <button
            v-if="images.length"
            class="image-expand"
            aria-label="Enlarge product image"
            @click="lightbox.showModal()"
          >
            <img
              :src="productImageUrl(images[activeIndex])"
              :alt="`${product.name} — image ${activeIndex + 1}`"
            /><span>⤢ Enlarge</span>
          </button>
          <ProductArtwork v-else :product="product" />
          <span v-if="state === 'soon'" class="availability-pill"
            >↗ COMING SOON</span
          >
        </div>
        <div v-if="images.length > 1" class="gallery-controls">
          <button class="button" aria-label="Previous image" @click="move(-1)">
            ←</button
          ><span>IMAGE {{ activeIndex + 1 }} / {{ images.length }}</span
          ><button class="button" aria-label="Next image" @click="move(1)">
            →
          </button>
        </div>
        <div v-if="images.length > 1" class="gallery-thumbnails">
          <button
            v-for="(src, i) in images"
            :key="i"
            :aria-label="`View image ${i + 1}`"
            :aria-pressed="activeIndex === i"
            @click="activeIndex = i"
          >
            <img
              :src="productImageUrl(src)"
              :alt="`${product.name} thumbnail ${i + 1}`"
            />
          </button>
        </div>
        <p v-if="product.releaseNote" class="release-note">
          {{ product.releaseNote }}
        </p>
      </div>
      <div class="product-information">
        <p class="eyebrow">
          {{ product.sku }} / {{ product.category }} DIVISION
        </p>
        <h1>{{ product.name }}</h1>
        <ProductTags :ids="product.tags" />
        <p class="detail-short">{{ product.shortDescription }}</p>
        <div class="detail-price">
          {{
            product.pricePending
              ? "Pricing to be announced"
              : product.price === 0
                ? "FREE"
                : formatPrice(product.price)
          }}
          <del
            v-if="
              !product.pricePending && product.compareAtPrice > product.price
            "
            >{{ formatPrice(product.compareAtPrice) }}</del
          ><small v-if="!product.pricePending">USD</small>
        </div>
        <p class="product-description">{{ product.description }}</p>
        <div v-if="state === 'soon'" class="coming-soon-panel">
          <span>↗</span>
          <div>
            <strong>GOOD THINGS ARE COMING.</strong>
            <p>
              This product is in development. Check back here for release
              details.
            </p>
          </div>
        </div>
        <p v-else class="stock-line">
          <span class="status-dot" />{{
            product.pricePending
              ? "Release details to be announced"
              : product.type === "digital" && state !== "out"
                ? "Digital release"
                : stockLabel(product)
          }}
        </p>
        <div v-if="purchasable" class="purchase-actions">
          <a
            v-if="freeDownload"
            :href="freeDownload"
            target="_blank"
            rel="noopener noreferrer"
            class="button primary"
            >↓ Free download <span>↗</span></a
          >
          <template v-else>
            <label class="quantity-field"
              >Quantity<input
                v-model.number="qty"
                type="number"
                min="1"
                :max="maxQty"
            /></label>
            <button class="button" @click="addToCart">Add to cart +</button>
            <button
              class="button primary"
              :disabled="
                checkout.loading ||
                !catalog.settings.checkoutEnabled ||
                catalog.preview
              "
              @click="buyNow"
            >
              {{ checkout.loading ? "Opening checkout…" : "Buy now ↗" }}
            </button>
          </template>
        </div>
        <p
          v-if="
            purchasable && !freeDownload && !catalog.settings.checkoutEnabled
          "
          class="release-note"
        >
          Online checkout is getting ready. You can save this item in your cart.
        </p>
        <div v-if="githubLink" class="resource-links">
          <a
            :href="githubLink"
            target="_blank"
            rel="noopener noreferrer"
            class="button"
            >⌘ Explore on GitHub ↗</a
          ><small>Source, documentation & project updates</small>
        </div>
        <section
          v-if="Object.keys(product.specs || {}).length"
          class="specifications"
        >
          <h2>AT A GLANCE</h2>
          <dl>
            <template v-for="(value, key) in product.specs" :key="key"
              ><dt>{{ key }}</dt>
              <dd>{{ value }}</dd></template
            >
          </dl>
        </section>
      </div>
    </div>
    <dialog
      ref="lightbox"
      class="image-lightbox"
      @click="$event.target === lightbox && lightbox.close()"
      @keydown.left="move(-1)"
      @keydown.right="move(1)"
    >
      <button class="button lightbox-close" autofocus @click="lightbox.close()">
        Close ×</button
      ><img
        v-if="images.length"
        :src="productImageUrl(images[activeIndex])"
        :alt="product.name"
      />
      <div v-if="images.length > 1" class="gallery-controls">
        <button
          class="button"
          aria-label="Previous enlarged image"
          @click="move(-1)"
        >
          ←</button
        ><span>{{ activeIndex + 1 }} / {{ images.length }}</span
        ><button
          class="button"
          aria-label="Next enlarged image"
          @click="move(1)"
        >
          →
        </button>
      </div>
    </dialog>
  </div>
</template>
