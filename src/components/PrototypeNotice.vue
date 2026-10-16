<script setup>
defineProps({ product: { type: Object, required: true }, compact: Boolean });
</script>
<template>
  <aside v-if="product.prototypeWarning" class="prototype-notice" role="note">
    <strong>TESTING NOT COMPLETE</strong>
    <p v-if="!compact">{{ product.prototypeWarning }}</p>
  </aside>
</template>
<style scoped>
.prototype-notice { margin: 1rem 0; padding: .8rem 1rem; border: 2px solid #ff7777; background: #50191d; color: #fff3f3; border-radius: .35rem; }
.prototype-notice strong { display: block; font-size: .8rem; letter-spacing: .05em; }
.prototype-notice p { margin: .4rem 0 0; font-size: .9rem; line-height: 1.5; color: #fff3f3; }
</style>
