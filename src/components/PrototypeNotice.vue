<script setup>
defineProps({ product: { type: Object, required: true }, compact: Boolean });
</script>
<template>
  <aside v-if="product.prototypeWarning" class="prototype-notice" :class="{ compact }" role="note">
    <strong>TESTING NOT COMPLETE</strong>
    <p v-if="!compact">{{ product.prototypeWarning }}</p>
  </aside>
</template>
<style scoped>
.prototype-notice { margin: 1rem 0; padding: .75rem 0; border-block: 1px solid var(--rule); color: var(--color-text); }
.prototype-notice strong { display: inline-block; font: 700 12px/1.5 var(--font-mono); letter-spacing: .04em; color: #ff7777; border-bottom: 2px solid currentColor; }
.prototype-notice p { margin: .4rem 0 0; font-size: 12px; line-height: 1.7; color: var(--color-text-dim); }
.prototype-notice.compact { margin: .5rem 0; padding: 0; border: 0; }
.prototype-notice.compact strong { font-size: 10px; }
</style>
