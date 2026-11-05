<script setup>
import source from '../../public/img/commander-x16/logo-color.svg?raw';
defineProps({ label: { type: String, required: true } });
// Supplied vector lettering and rainbow symbol, without the navy plaque.
// Only the white lettering follows the site's theme; the rainbow stays intact.
const artwork = source.match(/<g id="Rectangle_Color">([\s\S]*)<\/g>/)[1]
  .replace(/<path fill="#10192F"[\s\S]*?\/>/, '')
  .replaceAll('fill="#FFFFFF"', 'fill="currentColor"');
</script>

<template>
  <h1 class="x16-product-title" :aria-label="`Commander X16 ${label}`">
    <svg class="x16-title-wordmark" xmlns="http://www.w3.org/2000/svg"
      viewBox="730 380 6770 725" aria-hidden="true" v-html="artwork" />
    <span class="x16-title-name">{{ label }}</span>
  </h1>
</template>

<style scoped>
h1.x16-product-title{display:flex;flex-direction:column;gap:16px;margin:22px 0 24px;text-transform:none;letter-spacing:-.055em;color:var(--color-text)}
.x16-title-wordmark{display:block;width:100%;max-width:390px;height:auto;overflow:visible}
.x16-title-name{display:block;font:800 clamp(38px,4.5vw,58px)/1.03 var(--font-sans);letter-spacing:-.055em;text-transform:none;text-wrap:balance}
@media(max-width:480px){.x16-title-name{font-size:40px}.x16-title-wordmark{max-width:330px}}
</style>
