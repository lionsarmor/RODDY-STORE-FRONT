<script setup>
import { computed, ref, watch } from "vue";
import {
  useCatalogStore,
  stockState,
  stockLabel,
  formatPrice,
  productImageUrl,
} from "../stores/catalog";
import { merchVariants, optionValues, findVariant, priceLabel, shippingFor } from "../merch.js";
import { safeLink } from "../catalog-model.js";
import { useCartStore } from "../stores/cart";
import { useUiStore } from "../stores/ui";
import { useCheckoutStore } from "../stores/checkout";
import ProductTags from "../components/ProductTags.vue";
import ProductArtwork from "../components/ProductArtwork.vue";
import ProductCard from "../components/ProductCard.vue";
import RoddyLogo from "../components/RoddyLogo.vue";
import { departmentDirection } from "../department-data";
const props = defineProps({ id: { type: String, required: true } });
const catalog = useCatalogStore();
const cart = useCartStore();
const ui = useUiStore();
const checkout = useCheckoutStore();
const product = computed(() => catalog.byId(props.id));
const state = computed(() =>
  product.value ? stockState(product.value) : "out",
);
const selectedColor = ref("");
const selectedSize = ref("");
const destination = ref("US");
const variants = computed(() => merchVariants(product.value));
const colors = computed(() => optionValues(product.value, "color"));
const sizes = computed(() => optionValues(product.value, "size"));
const selectedVariant = computed(() => findVariant(product.value, selectedColor.value, selectedSize.value));
const selectedShipping = computed(() => shippingFor(product.value, selectedVariant.value, destination.value));
const selectionValid = computed(() => !product.value?.merch || (selectedVariant.value && selectedVariant.value.available === true));
watch(() => product.value?.merch, () => {
  selectedColor.value = colors.value.includes("Black") ? "Black" : colors.value[0] || "";
  selectedSize.value = variants.value.find(v => v.color === selectedColor.value && v.available === true)?.size || variants.value.find(v => v.color === selectedColor.value)?.size || "";
}, {immediate: true});
watch(selectedColor, () => {
  if (!selectedVariant.value) selectedSize.value = variants.value.find(v => v.color === selectedColor.value && v.available === true)?.size || variants.value.find(v => v.color === selectedColor.value)?.size || "";
});
function colorSwatch(color) {
  return variants.value.find(v => v.color === color)?.colors?.[0] || "transparent";
}
const qty = ref(1);
const activeIndex = ref(0);
watch(() => selectedVariant.value?.id, () => { activeIndex.value = 0; });
function chooseColor(color) {
  selectedColor.value = color;
  activeIndex.value = 0;
}
const expandedSpecs = ref(false);
const lightbox = ref(null);
const images = computed(() => [
  ...new Set([
    ...(selectedVariant.value?.image ? [selectedVariant.value.image] : []),
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
const documentationLink = computed(() =>
  safeLink(product.value?.documentationUrl),
);
const department = computed(() =>
  catalog.categoryMeta(product.value?.category),
);
const direction = computed(() => departmentDirection(product.value?.category));
const specifications = computed(() =>
  Object.entries(product.value?.specs || {}),
);
const visibleSpecifications = computed(() =>
  expandedSpecs.value ? specifications.value : specifications.value.slice(0, 6),
);
const isHardware = computed(
  () =>
    product.value?.type === "physical" &&
    ["computers", "pocket", "labs", "apps"].includes(product.value?.category),
);
const related = computed(() =>
  catalog
    .byCategory("all")
    .filter((p) => p.id !== props.id)
    .sort(
      (a, b) =>
        Number(b.category === product.value?.category) -
          Number(a.category === product.value?.category) ||
        Number(b.featured) - Number(a.featured),
    )
    .slice(0, 3),
);
const maxQty = computed(() =>
  product.value?.type === "digital"
    ? 1
    : product.value?.trackStock
      ? Math.min(99, product.value.stock)
      : 99,
);
watch(
  () => props.id,
  () => {
    activeIndex.value = 0;
    expandedSpecs.value = false;
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
  if (!purchasable.value || !selectionValid.value) return;
  cart.add(product.value.id, quantity(), maxQty.value, selectedVariant.value?.id || "");
  ui.toast(`Added ${product.value.name} to cart`);
}
async function buyNow() {
  if (product.value.type !== "digital") return;
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
  <div
    v-else
    class="product-page product-launch"
    :data-motif="direction.motif"
    :class="{ 'is-development': state === 'soon' }"
  >
    <nav class="product-breadcrumb" aria-label="Breadcrumb">
      <RouterLink to="/shop">Catalog</RouterLink><span>/</span
      ><RouterLink :to="{ path: '/shop', query: { cat: product.category } }">{{
        catalog.categoryMeta(product.category)?.name
      }}</RouterLink
      ><span>/</span><span>{{ product.name }}</span>
    </nav>
    <div class="launch-masthead">
      <span>{{ department?.name || product.category }} / RODDY DIVISION</span
      ><span>{{
        department?.code || "PERSONAL TECHNOLOGY. UNREASONABLE POSSIBILITIES."
      }}</span
      ><RoddyLogo kind="badge" />
    </div>
    <div class="product-detail-grid">
      <div class="product-gallery">
        <div class="plate-annotation">
          <span>{{ product.sku }} / THE EXHIBIT</span
          ><span>{{
            state === "soon" ? "IN DEVELOPMENT" : "TAKE A CLOSER LOOK"
          }}</span>
        </div>
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
        </div>
        <div class="plate-annotation">
          <span>{{
            state === "soon"
              ? "COMING SOON / NOT YET FOR SALE"
              : product.type === "digital"
                ? "FROM THE RODDY SOFTWARE LIBRARY"
                : "FROM THE RODDY COLLECTION"
          }}</span
          ><span aria-hidden="true">+ + +</span>
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
            selectedVariant && !product.pricePending
              ? formatPrice(selectedVariant.price)
              : priceLabel(product)
          }}
          <del
            v-if="
              !product.pricePending && product.compareAtPrice > (selectedVariant?.price ?? product.price)
            "
            >{{ formatPrice(product.compareAtPrice) }}</del
          ><small v-if="!product.pricePending && product.price > 0">USD</small>
        </div>
        <section v-if="product.merch" class="merch-options" aria-label="Choose merchandise options">
          <fieldset v-if="colors.length">
            <legend>Color <strong>{{ selectedColor }}</strong></legend>
            <div class="merch-choice-list">
              <button v-for="color in colors" :key="color" type="button" :aria-pressed="selectedColor === color" @click="chooseColor(color)">
                <span class="merch-swatch" :style="{background: colorSwatch(color)}" aria-hidden="true"></span>{{ color }}
              </button>
            </div>
          </fieldset>
          <fieldset v-if="sizes.length">
            <legend>Size <strong>{{ selectedSize }}</strong></legend>
            <div class="merch-choice-list">
              <button v-for="size in sizes" :key="size" type="button" :disabled="!findVariant(product, selectedColor, size)" :aria-pressed="selectedSize === size" @click="selectedSize = size">{{ size }}<span v-if="!findVariant(product, selectedColor, size)"> · Unavailable</span></button>
            </div>
          </fieldset>
          <p v-if="selectedVariant?.available === false" class="notice" role="status">This color and size is out of stock. Please choose another combination.</p>
          <p v-else-if="selectedVariant?.available !== true" class="notice">Availability needs confirmation before ordering.</p>
          <label class="merch-destination">Ship to
            <select v-model="destination"><option v-for="country in product.merch.shippingCountries" :key="country" :value="country">{{ country === 'US' ? 'United States' : country === 'CA' ? 'Canada' : country }}</option></select>
          </label>
          <p class="merch-shipping" v-if="selectedShipping">Standard shipping estimate: <strong>{{ formatPrice(selectedShipping.firstItem) }}</strong> for the first item; {{ formatPrice(selectedShipping.additionalItem) }} per additional item. USD. Final shipping depends on the delivery address.</p>
          <p v-else class="merch-shipping">Shipping estimate unavailable for this selection and destination. Shipping will be confirmed before payment.</p>
          <p class="merch-shipping">Made to order. Merchandise ordering opens soon; you can save your selection in your cart.</p>
        </section>
        <div v-if="state === 'soon'" class="coming-soon-panel">
          <span>↗</span>
          <div>
            <strong>ON THE WORKBENCH. NOT ON THE SHELF. YET.</strong>
            <p>
              Coming soon. This project is still in development and is not
              available to order. Follow its progress right here.
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
            <button class="button" :disabled="!selectionValid" @click="addToCart">Add to cart +</button>
            <button
              v-if="product.type === 'digital'"
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
        <p class="launch-signoff">INDEPENDENT IDEAS. A VERY PERSONAL FUTURE.</p>
      </div>
    </div>
    <section
      v-if="specifications.length"
      class="product-highlights"
      aria-label="Product highlights"
    >
      <div v-for="([key, value], i) in specifications.slice(0, 3)" :key="key">
        <span class="eyebrow">0{{ i + 1 }} / {{ key }}</span>
        <p>{{ value }}</p>
      </div>
    </section>
    <div class="product-editorial">
      <section class="product-story" aria-labelledby="product-story-heading">
        <p class="eyebrow">01 / THE IDEA</p>
        <h2 id="product-story-heading">
          A LITTLE MORE<br />TO THE STORY<span>.</span>
        </h2>
        <p class="product-description">
          {{ product.description || product.shortDescription }}
        </p>
        <template v-if="product.story"
          ><h3>WHY WE MADE IT</h3>
          <p class="product-description">{{ product.story }}</p></template
        >
        <div class="makers-signature">
          <RoddyLogo kind="full_logo" /><span
            >FROM OUR CORNER<br />OF THE FUTURE.</span
          >
        </div>
      </section>
      <section
        v-if="specifications.length"
        class="specifications launch-specifications"
        aria-labelledby="specifications-heading"
      >
        <p class="eyebrow">02 / THE DETAILS</p>
        <h2 id="specifications-heading">AT A GLANCE<span>↘</span></h2>
        <dl id="product-specification-list">
          <template v-for="[key, value] in visibleSpecifications" :key="key"
            ><dt>{{ key }}</dt>
            <dd>{{ value }}</dd></template
          >
        </dl>
        <button
          v-if="specifications.length > 6"
          class="text-button specifications-toggle"
          :aria-expanded="expandedSpecs"
          aria-controls="product-specification-list"
          @click="expandedSpecs = !expandedSpecs"
        >
          {{
            expandedSpecs
              ? "Show fewer specifications −"
              : `Show all ${specifications.length} specifications +`
          }}
        </button>
        <p v-if="state === 'soon'" class="release-note">
          In development. Specifications may change before release.
        </p>
      </section>
    </div>
    <section
      v-if="isHardware || documentationLink || githubLink"
      class="product-documentation"
      aria-labelledby="documentation-heading"
    >
      <div>
        <p class="eyebrow">THE OPEN-DOOR POLICY</p>
        <h2 id="documentation-heading">
          {{
            isHardware
              ? "OPEN IT. UNDERSTAND IT. REPAIR IT."
              : "GO BEYOND THE BOX."
          }}
        </h2>
      </div>
      <div>
        <p>
          {{
            isHardware
              ? "Made for human beings. Repairable by human beings. Our hardware promise: schematics, technical documentation, and repair information included. You should be able to understand the machine you own."
              : "Curiosity should not stop at the product page. Find the project resources and get to know what makes this one tick."
          }}
        </p>
        <div class="documentation-actions">
          <a
            v-if="documentationLink"
            :href="documentationLink"
            target="_blank"
            rel="noopener noreferrer"
            class="button primary"
            >{{
              isHardware
                ? "Documentation & schematics"
                : "Read the documentation"
            }}
            ↗</a
          ><a
            v-if="githubLink"
            :href="githubLink"
            target="_blank"
            rel="noopener noreferrer"
            class="button"
            >Explore on GitHub ↗</a
          ><RouterLink v-if="isHardware" to="/about" class="text-button"
            >Read our promise ↗</RouterLink
          >
        </div>
        <p v-if="isHardware && !documentationLink" class="release-note">
          {{
            state === "soon"
              ? "Project documentation will be linked here when it is published."
              : "Documentation is not linked here yet. Check back for the published resources."
          }}
        </p>
      </div>
    </section>
    <section
      v-if="related.length"
      class="product-related"
      aria-labelledby="related-heading"
    >
      <div class="directory-list-heading">
        <div>
          <p class="eyebrow">KEEP EXPLORING</p>
          <h2 id="related-heading">There is more on the shelf.</h2>
        </div>
        <RouterLink to="/shop" class="text-button">Full catalog ↗</RouterLink>
      </div>
      <div class="catalog-grid">
        <ProductCard v-for="p in related" :key="p.id" :product="p" />
      </div>
    </section>
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
