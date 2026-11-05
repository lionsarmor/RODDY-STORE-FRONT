<script setup>
import { rawAssetUrl } from '../config';
const badge = rawAssetUrl('img/commander-x16/official-partner.svg');
function star(outer, inner) {
  return Array.from({length:48},(_,i)=>{
    const angle=(i*7.5-90)*Math.PI/180,r=i%2?inner:outer;
    return `${(150+Math.cos(angle)*r).toFixed(3)},${(150+Math.sin(angle)*r).toFixed(3)}`;
  }).join(' ');
}
</script>

<template>
  <aside class="x16-partner" aria-label="Commander X16 partnership">
    <RouterLink to="/product/x16-keycaps" class="x16-sticker" aria-label="RODDY is a Commander X16 Official Partner — explore keycaps">
      <svg class="x16-sticker-art" viewBox="-6 -6 312 312" role="img" aria-label="RODDY — Commander X16 Official Partner">
        <polygon :points="star(150,136)" fill="#faf4df" />
        <polygon :points="star(144,130)" fill="#577cbd" />
        <polygon :points="star(138,124)" fill="#10192d" />
        <g fill="#faf4df" aria-hidden="true">
          <text x="150" y="69" text-anchor="middle" class="x16-roddy">RODDY</text>
          <path d="M71 65l3-8 3 8 8 3-8 3-3 8-3-8-8-3zM223 65l3-8 3 8 8 3-8 3-3 8-3-8-8-3z" />
        </g>
        <image :href="badge" x="36" y="91" width="228" height="118" preserveAspectRatio="xMidYMid meet" />
        <g aria-hidden="true">
          <path d="M109 230h17" stroke="#ab5fa6" stroke-width="4" /><path d="M126 230h16" stroke="#68c8f2" stroke-width="4" /><path d="M142 230h16" stroke="#95c940" stroke-width="4" /><path d="M158 230h16" stroke="#fbb21d" stroke-width="4" /><path d="M174 230h17" stroke="#ee2f34" stroke-width="4" />
          <text x="150" y="251" text-anchor="middle" class="x16-tagline" fill="#faf4df">BUILD. PLAY. MAKE IT YOURS.</text>
        </g>
      </svg>
    </RouterLink>
  </aside>
</template>

<style scoped>
.x16-partner{width:clamp(150px,18vw,210px);max-width:100%;margin:0 auto;padding:14px;isolation:isolate}
.x16-sticker{display:block;aspect-ratio:1;text-decoration:none;transform:rotate(-7deg);filter:drop-shadow(0 3px 0 #142e76) drop-shadow(0 7px 8px #0002);transition:transform .18s}
.x16-sticker-art{width:100%;height:100%;display:block;overflow:visible}.x16-roddy{font:900 17px Arial,sans-serif;letter-spacing:4px}.x16-tagline{font:700 8px Arial,sans-serif;letter-spacing:.8px}
.x16-sticker:hover{transform:rotate(-3deg)}.x16-sticker:focus-visible{outline:3px solid var(--color-brand);outline-offset:8px}
@media(prefers-reduced-motion:reduce){.x16-sticker{transition:none}}
</style>
