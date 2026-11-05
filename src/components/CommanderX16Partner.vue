<script setup>
import { rawAssetUrl } from '../config';
const badge = rawAssetUrl('img/commander-x16/official-partner.svg');
</script>

<template>
  <aside class="x16-partner-credit" aria-label="RODDY is a Commander X16 official partner">
    <RouterLink to="/product/x16-keycaps" class="x16-partner-link" aria-label="Commander X16 Official Partner — explore RODDY keycaps">
      <img :src="badge" alt="Commander X16 Official Partner" width="8000" height="4136" loading="lazy" />
    </RouterLink>
    <p>Independent ideas for the<br />Commander X16 community.</p>
  </aside>
</template>

<style scoped>
.x16-partner-credit{display:flex;align-items:center;gap:18px;padding-top:22px;border-top:1px solid var(--color-border);margin-top:24px}
.x16-partner-link{display:block;flex:0 0 150px;max-width:45%}
.x16-partner-link img{display:block;width:100%;height:auto}
.x16-partner-link:focus-visible{outline:2px solid var(--color-brand);outline-offset:5px}
.x16-partner-credit p{font-size:12px;line-height:1.6;color:var(--color-text-dim);margin:0}
@media(max-width:480px){.x16-partner-credit{gap:14px}.x16-partner-link{flex-basis:125px}.x16-partner-credit p{font-size:11px}}
</style>
