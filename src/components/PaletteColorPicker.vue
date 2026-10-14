<script setup>
import {computed,ref,useId,nextTick} from 'vue';
import {KEYCAP_COLORS,colorHex,colorName} from '../keycap-palette.js';
const props=defineProps({modelValue:String,label:{type:String,default:'Choose a color'},disabled:Boolean});
const emit=defineEmits(['update:modelValue']);
const dialog=ref(null),searchInput=ref(null),query=ref(''),family=ref(''),isOpen=ref(false);
const heading=useId();
const families={GR:'Neutrals',BL:'Blues',GN:'Greens',YW:'Yellows',OG:'Oranges',RD:'Reds',PK:'Pinks',PL:'Purples',BN:'Browns'};
const colors=computed(()=>{
  const term=query.value.trim().toLowerCase();
  return KEYCAP_COLORS.filter(c=>(!family.value||c.id.startsWith(family.value))&&(!term||`${c.id} ${c.name} ${c.hex}`.toLowerCase().includes(term)));
});
async function open(){query.value='';family.value='';isOpen.value=true;await nextTick();dialog.value.showModal();searchInput.value?.focus();}
function choose(id){emit('update:modelValue',id);dialog.value.close();}
</script>
<template>
  <div class="keycap-color-picker">
    <button type="button" class="color-trigger" :disabled="disabled" @click="open" :aria-label="`${label}: ${colorName(modelValue)}`" aria-haspopup="dialog">
      <i :style="{background:colorHex(modelValue)}" aria-hidden="true"/><span><strong>{{label}}</strong><small>{{colorName(modelValue)}}</small></span><b aria-hidden="true">↗</b>
    </button>
    <Teleport to="body">
      <dialog ref="dialog" class="keycap-palette-dialog" :aria-labelledby="heading" @click="e=>{if(e.target===dialog)dialog.close()}" @close="isOpen=false"><template v-if="isOpen">
        <div class="palette-heading"><div><p>RODDY COLOR SELECTION</p><h3 :id="heading">{{label}}</h3></div><button type="button" class="palette-close" aria-label="Close color picker" @click="dialog.close()">×</button></div>
        <p class="palette-help">Choose from {{KEYCAP_COLORS.length}} available colors. Screen colors can differ from the printed set.</p>
        <div class="palette-filters"><label>Search colors<input ref="searchInput" v-model="query" type="search" placeholder="Color name or code" /></label><label>Color family<select v-model="family"><option value="">All colors</option><option v-for="(name,id) in families" :key="id" :value="id">{{name}}</option></select></label></div>
        <div class="palette-results" aria-live="polite">{{colors.length}} colors · selected {{colorName(modelValue)}}</div>
        <div class="palette-grid"><button v-for="color in colors" :key="color.id" type="button" :aria-label="`${color.name} · ${color.id}`" :aria-pressed="color.id===modelValue" :title="`${color.name} · ${color.id}`" @click="choose(color.id)"><i :style="{background:color.hex}" aria-hidden="true"/><span>{{color.name}}</span><small>{{color.id}}</small></button></div>
        <p v-if="!colors.length" class="palette-help">No matching colors. Try another name or color family.</p>
      </template></dialog>
    </Teleport>
  </div>
</template>
<style>
.color-trigger{display:flex;align-items:center;gap:12px;width:100%;padding:10px 0;border:0;border-bottom:1px solid var(--color-border,#444);text-align:left;background:transparent;color:inherit;cursor:pointer}.color-trigger:disabled{opacity:.5;cursor:default}.color-trigger>i{display:block;width:38px;height:38px;border:1px solid #ffffff45;border-radius:6px;flex-shrink:0}.color-trigger>span{flex:1;min-width:0}.color-trigger strong{display:block;font-size:13px;font-weight:600}.color-trigger small{display:block;font-size:11px;margin-top:4px;opacity:.7}.color-trigger b{font-size:18px}.keycap-palette-dialog{box-sizing:border-box;width:min(720px,calc(100vw - 24px));max-height:88dvh;padding:24px;border:1px solid #535663;border-radius:14px;background:#181a20;color:#F7F7F5;overflow-y:auto;margin:auto;box-shadow:0 24px 80px #0009;font-family:inherit}.keycap-palette-dialog::backdrop{background:#000b;backdrop-filter:blur(3px)}.palette-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}.palette-heading p{font:10px monospace;letter-spacing:2px;color:#93B0DB;margin:0 0 8px}.palette-heading h3{font-size:25px;margin:0}.palette-close{border:1px solid #535663;background:transparent;color:inherit;border-radius:6px;min-width:36px;height:36px;font-size:24px;cursor:pointer}.palette-help{font-size:12px;line-height:1.6;color:#b7bac3;margin:16px 0}.palette-filters{display:grid;grid-template-columns:1.5fr 1fr;gap:12px}.palette-filters label{display:grid;gap:6px;font-size:11px}.palette-filters input,.palette-filters select{width:100%;box-sizing:border-box;padding:10px;border:1px solid #535663;border-radius:5px;background:#242731;color:#F7F7F5;font:13px inherit}.palette-results{font:11px monospace;color:#b7bac3;margin:16px 0}.palette-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(82px,1fr));gap:9px}.palette-grid button{display:flex;flex-direction:column;align-items:stretch;gap:5px;padding:7px;border:1px solid #454854;border-radius:7px;background:#242731;color:#F7F7F5;cursor:pointer;min-width:0;text-align:left}.palette-grid button[aria-pressed=true]{border-color:#93B0DB;box-shadow:0 0 0 1px #93B0DB}.palette-grid i{height:42px;border-radius:3px;border:1px solid #ffffff35}.palette-grid span{font-size:10px;line-height:1.25;overflow-wrap:anywhere}.palette-grid small{font:9px monospace;opacity:.65}.palette-grid button:focus-visible,.color-trigger:focus-visible,.palette-close:focus-visible{outline:3px solid #93B0DB;outline-offset:2px}@media(max-width:480px){.keycap-palette-dialog{padding:17px}.palette-filters{grid-template-columns:1fr}.palette-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
</style>
