<script setup>
import {computed} from 'vue';
const props=defineProps({design:Object});
const bounds=computed(()=>{const keys=props.design.layoutKeys;const x=Math.min(...keys.map(k=>k.x)),y=Math.min(...keys.map(k=>k.y));const w=Math.max(...keys.map(k=>k.x+parseFloat(k.sizeId)))-x,h=Math.max(...keys.map(k=>k.y+1))-y;return {x,y,w,h};});
</script>
<template>
  <svg :viewBox="`0 0 ${bounds.w*1000+400} ${bounds.h*1000+400}`" role="img" aria-label="Live preview of your custom keycap design" class="keycap-preview">
    <rect width="100%" height="100%" rx="180" fill="#181c24" />
    <g v-for="key in design.layoutKeys" :key="key.id" :transform="`translate(${(key.x-bounds.x)*1000+200} ${(key.y-bounds.y)*1000+200})`">
      <title>{{key.labelId}}</title>
      <rect x="32" y="32" :width="parseFloat(key.sizeId)*1000-64" height="936" rx="95" :fill="design.keys[key.id].colorId" stroke="#00000055" stroke-width="24" />
      <g v-for="layer in design.keys[key.id].layers" :key="layer.id"><path :d="layer.vectDef" :fill="layer.colorId" /></g>
    </g>
  </svg>
</template>
<style scoped>.keycap-preview{display:block;width:100%;height:auto;min-width:650px;}</style>
