<script setup>
import RoddyLogo from "./RoddyLogo.vue";
defineProps({ product: { type: Object, required: true } });
</script>
<template>
  <div class="product-artwork" :class="product.category" aria-hidden="true">
    <template v-if="product.category === 'apps'">
      <div class="mini-window">
        <div class="mini-title">RODDY / DESK COMMANDER <span>■</span></div>
        <div class="mini-desktop">
          <span>▦<small>FILES</small></span
          ><span>▤<small>NOTES</small></span
          ><span>◴<small>FOCUS</small></span>
        </div>
        <div class="mini-prompt">READY FOR YOUR NEXT BIG IDEA.<b>_</b></div>
      </div>
    </template>
    <template v-else-if="product.category === 'computers'"
      ><RoddyLogo kind="badge" class="product-fallback-logo" />
      <span class="art-caption"
        >PROJECT KESTREL / IN DEVELOPMENT</span
      ></template
    >
    <template v-else
      ><RoddyLogo kind="badge" class="product-fallback-logo" />
      <span class="art-caption">{{ product.name }}</span></template
    >
  </div>
</template>
