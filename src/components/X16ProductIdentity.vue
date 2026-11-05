<script setup>
import { rawAssetUrl } from '../config';
</script>

<template>
  <div class="x16-product-identity" aria-label="Commander X16 collection by RODDY, an official partner">
    <img class="x16-wordmark" :src="rawAssetUrl('img/commander-x16/logo-color.svg')" alt="Commander X16" width="7993" height="1424" />
    <img class="x16-official-badge" :src="rawAssetUrl('img/commander-x16/official-partner.svg')" alt="RODDY is a Commander X16 Official Partner" width="8000" height="4136" />
  </div>
</template>

<style scoped>
.x16-product-identity{display:flex;align-items:center;justify-content:space-between;gap:24px;padding-bottom:20px;margin-bottom:24px;border-bottom:1px solid var(--color-border)}
.x16-wordmark{display:block;width:210px;max-width:60%;height:auto}
.x16-official-badge{display:block;width:104px;max-width:30%;height:auto;flex-shrink:0}
@media(max-width:480px){.x16-product-identity{gap:18px;padding-bottom:16px;margin-bottom:20px}.x16-wordmark{width:185px}.x16-official-badge{width:88px}}
</style>
