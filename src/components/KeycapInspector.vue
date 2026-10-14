<script setup>
import {ref,nextTick} from 'vue';
import KeycapPreview from './KeycapPreview.vue';
defineProps({design:Object});
const dialog=ref(null),zoom=ref(150);
async function open(){zoom.value=150;await nextTick();dialog.value.showModal();}
function adjust(amount){zoom.value=Math.min(400,Math.max(100,zoom.value+amount));}
defineExpose({open});
</script>
<template>
  <Teleport to="body"><dialog ref="dialog" class="keyboard-inspector" aria-labelledby="keyboard-inspector-title" @click="e=>{if(e.target===dialog)dialog.close()}">
    <header><h2 id="keyboard-inspector-title">Inspect your keycaps</h2><button type="button" aria-label="Close keyboard preview" @click="dialog.close()">×</button></header>
    <div class="inspector-controls"><button type="button" aria-label="Zoom out" :disabled="zoom<=100" @click="adjust(-50)">−</button><label>Zoom <input v-model.number="zoom" type="range" min="100" max="400" step="25" /> {{zoom}}%</label><button type="button" aria-label="Zoom in" :disabled="zoom>=400" @click="adjust(50)">+</button><button type="button" @click="zoom=100">Fit keyboard</button></div>
    <div class="inspector-scroll"><KeycapPreview v-if="design" :design="design" :style="{width:zoom+'%',minWidth:'0',maxWidth:'none'}" /></div>
  </dialog></Teleport>
</template>
<style scoped>
.keyboard-inspector{box-sizing:border-box;width:min(96vw,1800px);max-width:none;max-height:94dvh;padding:20px;border:1px solid #535663;border-radius:14px;background:#181a20;color:#FAF7F0;margin:auto}.keyboard-inspector::backdrop{background:#000c;backdrop-filter:blur(4px)}header{display:flex;align-items:center;justify-content:space-between;gap:16px}h2{font-size:22px;margin:0}button{border:1px solid #535663;border-radius:6px;padding:8px 12px}header button{font-size:26px;line-height:1}.inspector-controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:18px 0;font-size:13px}.inspector-controls label{display:flex;align-items:center;gap:10px}.inspector-controls input{width:150px}.inspector-scroll{overflow:auto;max-height:calc(94dvh - 150px);border-radius:8px;overscroll-behavior:contain}@media(max-width:540px){.keyboard-inspector{padding:14px}h2{font-size:18px}.inspector-controls{gap:8px}.inspector-controls input{width:90px}.inspector-scroll{max-height:calc(94dvh - 190px)}}
</style>
