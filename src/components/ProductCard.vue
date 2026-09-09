<script setup>
import {
  stockState,
  stockLabel,
  formatPrice,
  productImageUrl,
  useCatalogStore,
} from "../stores/catalog";
import ProductTags from "./ProductTags.vue";
import ProductArtwork from "./ProductArtwork.vue";
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
      ><span
        >{{
          stockState(product) === "soon"
            ? "LAB PREVIEW"
            : product.type === "digital"
              ? "SOFTWARE LIBRARY"
              : "RODDY ORIGINAL"
        }}
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
          ? "● COMING SOON"
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
      <p>{{ product.shortDescription || product.description }}</p>
      <ProductTags :ids="product.tags" />
      <div class="product-card-bottom">
        <span
          >{{
            product.pricePending
              ? "Details to come"
              : product.price === 0
                ? "FREE"
                : formatPrice(product.price)
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
              ? "Explore project"
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
