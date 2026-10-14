<script setup>
defineProps({design:Object});
</script>
<template>
  <svg :viewBox="`0 0 ${design.width} ${design.height}`" role="img" aria-label="Live preview of your custom keycap design" class="keycap-preview">
    <rect width="100%" height="100%" rx="180" fill="#181c24" />
    <g v-for="(key,index) in design.keys" :key="index" :transform="`translate(${key.x} ${key.y})`">
      <title>{{key.label}}</title>
      <rect x="32" y="32" :width="key.width" height="936" rx="95" :fill="key.color" stroke="#00000055" stroke-width="24" />
      <path v-for="(shape,i) in key.shapes" :key="i" :d="shape.path" :fill="shape.fill" />
    </g>
  </svg>
</template>
<style scoped>.keycap-preview{display:block;width:100%;height:auto;min-width:650px;}</style>
