<script setup>
import {colorName} from '../keycap-palette.js';
defineProps({design:Object,interactive:Boolean,selectedKeys:{type:Array,default:()=>[]}});
const emit=defineEmits(['select-key']);
</script>
<template>
  <svg :viewBox="`0 0 ${design.width} ${design.height}`" :role="interactive?'group':'img'" :aria-label="interactive?'Choose individual keys to recolor':'Live preview of your custom keycap design'" class="keycap-preview" :class="{interactive}">
    <rect width="100%" height="100%" rx="180" fill="#181c24" />
    <g v-for="(key,index) in design.keys" :key="key.id || index" :transform="`translate(${key.x} ${key.y})`" :role="interactive?'button':undefined" :tabindex="interactive?0:undefined" :aria-label="interactive?`${key.name}: ${colorName(key.paletteId)}`:undefined" :aria-pressed="interactive?selectedKeys.includes(key.id):undefined" :data-key="key.id" @click="interactive&&emit('select-key',key.id)" @keydown.enter.prevent="interactive&&emit('select-key',key.id)" @keydown.space.prevent="interactive&&emit('select-key',key.id)">
      <title>{{key.name || key.label}}</title>
      <rect x="32" y="32" :width="key.width" height="936" rx="95" :fill="key.color" :stroke="selectedKeys.includes(key.id)?'#F06434':'#00000055'" :stroke-width="selectedKeys.includes(key.id)?65:24" />
      <path v-for="(shape,i) in key.shapes" :key="i" :d="shape.path" :fill="shape.fill" />
      <circle v-if="key.custom" :cx="key.width-48" cy="866" r="28" fill="#F06434" stroke="#181c24" stroke-width="12" aria-hidden="true"/>
    </g>
  </svg>
</template>
<style scoped>.keycap-preview{display:block;width:100%;height:auto;min-width:650px}.interactive g{cursor:pointer}.interactive g:focus{outline:none}.interactive g:focus-visible>rect{stroke:#FAF7F0;stroke-width:65}</style>
