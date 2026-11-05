<script setup>
import source from '../../public/img/commander-x16/logo-color.svg?raw';
defineProps({ label: { type: String, required: true }, compact: Boolean });
// Supplied vector lettering and rainbow symbol, without the navy plaque.
// Only the white lettering follows the site's theme; the rainbow stays intact.
const artwork = source.match(/<g id="Rectangle_Color">([\s\S]*)<\/g>/)[1]
  .replace(/<path fill="#10192F"[\s\S]*?\/>/, '')
  .replaceAll('fill="#FFFFFF"', 'fill="currentColor"');
</script>

<template>
  <component :is="compact ? 'h3' : 'h1'" class="x16-product-title" :class="{ 'is-compact': compact }" :aria-label="`Commander X16 ${label} by RODDY, official partner`">
    <span class="x16-partner-label">Official partner</span>
    <svg class="x16-title-wordmark" xmlns="http://www.w3.org/2000/svg"
      viewBox="730 380 6770 725" aria-hidden="true" v-html="artwork" />
    <span class="x16-title-name">{{ label }}</span>
  </component>
</template>

<style scoped>
@font-face{font-family:"X16 Product";src:url("/fonts/michroma/Michroma-Regular.ttf") format("truetype");font-weight:400;font-style:normal;font-display:swap}
h1.x16-product-title,h3.x16-product-title{display:flex;flex-direction:column;gap:0;width:100%;max-width:390px;margin:22px 0 24px;color:var(--color-text)}
.x16-partner-label{display:block;margin-bottom:0;font:700 12px/1.2 var(--font-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--color-text)}
.x16-title-wordmark{display:block;width:100%;height:auto;overflow:visible}
.x16-title-name{display:block;font:400 clamp(20px,2.3vw,27px)/1.25 "X16 Product",sans-serif;letter-spacing:.025em;text-transform:uppercase;white-space:nowrap;-webkit-text-stroke:.4px currentColor}
@media(max-width:480px){h1.x16-product-title{max-width:330px}.x16-title-name{font-size:clamp(17px,5.3vw,23px)}}
h3.x16-product-title.is-compact{container-type:inline-size;max-width:300px;margin:0 0 4px}
.is-compact .x16-partner-label{font-size:clamp(8px,3cqw,10px)}
.is-compact .x16-title-name{font-size:clamp(12px,6.9cqw,21px);-webkit-text-stroke:.3px currentColor}
</style>
