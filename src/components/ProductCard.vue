<script setup>
import {
  stockState,
  stockLabel,
  formatPrice,
  productImageUrl,
} from "../stores/catalog";
import ProductTags from "./ProductTags.vue";
import ProductArtwork from "./ProductArtwork.vue";
defineProps({ product: { type: Object, required: true } });
</script>
<template>
  <RouterLink :to="`/product/${product.id}`" class="product-card">
    <div class="product-card-image">
      <img
        v-if="product.coverImage || product.images?.[0]"
        :src="productImageUrl(product.coverImage || product.images[0])"
        :alt="product.name"
        loading="lazy"
      />
      <ProductArtwork v-else :product="product" />
      <span class="catalog-number">{{ product.sku }}</span>
      <span v-if="stockState(product) === 'soon'" class="availability-pill"
        >↗ COMING SOON</span
      >
    </div>
    <div class="product-card-body">
      <span class="eyebrow">{{ product.category }} / RODDY</span>
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
              ? "Discover"
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
