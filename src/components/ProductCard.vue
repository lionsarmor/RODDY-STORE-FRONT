<script setup>
import {
  stockState,
  stockLabel,
  formatPrice,
  productImageUrl,
  useCatalogStore,
} from "../stores/catalog";
import { priceLabel } from "../merch.js";
import { shippingLabel } from '../shipping-destinations.js';
import ProductTags from "./ProductTags.vue";
import ProductArtwork from "./ProductArtwork.vue";
import { productOrigin } from '../product-origin.js';
defineProps({ product: { type: Object, required: true } });
const catalog = useCatalogStore();
</script>
<template>
  <RouterLink
    :to="`/product/${product.id}`"
    class="product-card"
    :class="{ 'is-development': stockState(product) === 'soon' }"
    :data-department="product.category"
  >
    <div class="product-plate-head">
      <span class="catalog-number">{{ product.sku }}</span
      ><span :title="product.projectCredit ? 'X16 playback project by ' + product.projectCredit.name : productOrigin(product).description"
        >{{ product.projectCredit?.name || productOrigin(product).label }}
        <span aria-hidden="true">↗</span></span
      >
    </div>
    <div class="product-card-image">
      <img
        v-if="product.coverImage || product.images?.[0]"
        :src="productImageUrl(product.coverImage || product.images[0])"
        :alt="product.name"
        loading="lazy"
      />
      <ProductArtwork v-else :product="product" />
    </div>
    <div class="product-plate-caption">
      <span
        >{{
          catalog.categoryMeta(product.category)?.name || product.category
        }}
        DIVISION</span
      ><span :class="{ 'development-label': stockState(product) === 'soon' }">{{
        stockState(product) === "soon"
          ? `● ${stockLabel(product).toUpperCase()}`
          : stockState(product) === "out"
            ? "SOLD OUT"
            : product.pricePending
              ? "DETAILS TO COME"
              : product.type === "digital"
                ? "DIGITAL RELEASE"
                : stockLabel(product)
      }}</span>
    </div>
    <div class="product-card-body">
      <h3>{{ product.name }}</h3>
      <p v-if="product.projectCredit" class="movie-card-credit">X16 playback by <strong>{{ product.projectCredit.name }}</strong></p>
      <p>{{ product.shortDescription || product.description }}</p>
      <ProductTags :ids="product.tags" /><p v-if="product.type === 'physical'" class="shipping-destinations">{{ shippingLabel(product) }}</p>
      <div class="product-card-bottom">
        <span
          >{{
            priceLabel(product)
          }}
          <del
            v-if="
              !product.pricePending && product.compareAtPrice > product.price
            "
            >{{ formatPrice(product.compareAtPrice) }}</del
          ></span
        ><span
          >{{
            stockState(product) === "soon"
              ? product.category === 'video' ? 'View movie' : 'Explore project'
              : stockState(product) === "out"
                ? stockLabel(product)
                : "Take a look"
          }}
          ↗</span
        >
      </div>
    </div>
  </RouterLink>
</template>
