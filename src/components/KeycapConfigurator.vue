<script setup>
import {computed,ref,watch} from 'vue';
import {ARROWS,MARKS,KEYCAP_TEMPLATES,DEFAULT_COLORS,defaultDesign,designError,generateDesign,downloadJson} from '../keycaps';
import KeycapPreview from './KeycapPreview.vue';
const props=defineProps({profile:Object,profiles:Array,products:Array});
const emit=defineEmits(['change','save']);
const selection=ref(null);
watch(()=>props.profile,p=>{selection.value=p?defaultDesign(p):null;},{immediate:true});
watch(selection,d=>emit('change',d?{...d}:null),{deep:true,immediate:true});
const error=computed(()=>designError(selection.value,props.profile));
const design=computed(()=>error.value?null:generateDesign(props.profile,selection.value));
const template=computed(()=>KEYCAP_TEMPLATES[props.profile?.templateId]);
const colorFields=[['alpha','Main keys'],['modifiers','Modifiers'],['accents','Accent keys']];
const presets=[{name:'V6 original',...DEFAULT_COLORS},{name:'Night flight',alpha:'#DCE4ED',modifiers:'#242A36',accents:'#C32D28'},{name:'Terminal',alpha:'#CFDBCD',modifiers:'#303E36',accents:'#83B697'},{name:'Signal',alpha:'#F5EEDB',modifiers:'#454251',accents:'#E6B24C'}];
const siblings=computed(()=>props.products?.filter(p=>p.active&&p.keycaps&&p.keycaps.profileId!==props.profile?.id)||[]);
function preset(p){for(const [k] of colorFields)selection.value[k]=p[k];}
</script>
<template>
  <section class="keycap-studio" aria-labelledby="keycap-studio-title">
    <div class="studio-heading"><div><p class="eyebrow">YOUR KEYBOARD. YOUR SIGNAL.</p><h2 id="keycap-studio-title">MAKE IT YOURS<span>.</span></h2></div><span class="studio-badge">{{profile?.name || 'Keyboard profile unavailable'}}</span></div>
    <p v-if="!template" class="notice">This keyboard profile needs a design template. Please check back soon.</p>
    <template v-else>
      <p class="studio-intro">{{profile.description}}</p>
      <div class="studio-grid">
        <div class="studio-controls">
          <fieldset><legend>01 / Set the palette</legend><div class="preset-list"><button v-for="p in presets" :key="p.name" type="button" @click="preset(p)"><span class="preset-swatches"><i :style="{background:p.alpha}" /><i :style="{background:p.modifiers}" /><i :style="{background:p.accents}" /></span>{{p.name}}</button></div>
            <label v-for="[id,label] in colorFields" :key="id" class="color-choice"><span>{{label}}<small>{{selection[id]}}</small></span><input v-model="selection[id]" type="color" :aria-label="label" @input="selection[id]=selection[id].toUpperCase()" /></label>
          </fieldset>
          <fieldset><legend>02 / Choose your Commander key</legend><div class="symbol-list"><button v-for="id in profile.marks || Object.keys(MARKS)" :key="id" :aria-pressed="selection.mark===id" @click="selection.mark=id"><svg viewBox="0 0 1250 1000" aria-hidden="true"><rect width="1250" height="1000" rx="90" :fill="selection.accents" /><path v-for="l in template.marks[id]" :key="l.id" :d="l.vectDef" :fill="l.colorId" /></svg><span>{{MARKS[id]}}</span></button></div></fieldset>
          <fieldset><legend>03 / Pick your arrows</legend><div class="arrow-list"><button v-for="id in profile.arrows || Object.keys(ARROWS)" :key="id" :aria-pressed="selection.arrows===id" @click="selection.arrows=id"><span :class="id" aria-hidden="true">↑</span>{{ARROWS[id]}}</button></div></fieldset>
          <div class="studio-actions"><button class="button primary" :disabled="!!error" @click="$emit('save')">Save design to cart +</button><button class="text-button" :disabled="!!error" @click="downloadJson(design,profile.id+'-yuzu.json')">Download design JSON ↓</button><button class="text-button" @click="selection=defaultDesign(profile)">Reset to profile defaults</button></div>
          <p v-if="error" role="alert" class="notice">{{error}}</p>
        </div>
        <div class="studio-proof"><div class="preview-scroll"><KeycapPreview v-if="design" :design="design" /></div><p class="proof-caption">LIVE DESIGN PREVIEW · {{template.base.layoutKeys.length}} KEYS · {{template.base.keycapProfileId.toUpperCase()}} PROFILE</p><p>{{template.compatibility}}</p><p class="proof-note">Colors are a screen preview. Number-row swatches and PETSCII artwork stay fixed. Check the final manufacturing proof before production.</p><p v-if="selection.arrows==='small-black'" class="proof-note">Small arrows and the Commander symbol use dark ink. Choose an accent color with enough contrast.</p><p class="studio-process">Choose a design → pay when ordering opens → RODDY reviews and submits your set to the maker. Keyboard sold separately.</p></div>
      </div>
      <nav v-if="siblings.length" class="profile-links" aria-label="Other keyboard sets"><strong>Explore other keyboard profiles</strong><RouterLink v-for="p in siblings" :key="p.id" :to="'/product/'+p.id">{{p.name}} ↗</RouterLink></nav>
    </template>
  </section>
</template>
<style scoped>
.keycap-studio{margin:4rem 0;padding:clamp(20px,4vw,48px);border:1px solid var(--color-border,#444);background:var(--color-panel,#101115);border-top:4px solid #7FAFD3}.studio-heading{display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap}.studio-heading h2{font-size:clamp(32px,5vw,64px);font-weight:900;line-height:1.1;margin:12px 0}.studio-heading h2 span{color:#C32D28}.studio-badge{border:1px solid var(--color-border,#444);padding:10px 14px;font:12px monospace}.studio-intro{max-width:760px;margin:12px 0 28px;color:var(--color-text-dim)}.studio-grid{display:grid;grid-template-columns:minmax(250px,340px) minmax(0,1fr);gap:32px}.studio-controls fieldset{margin-bottom:28px}.studio-controls legend{font:12px monospace;font-weight:bold;margin-bottom:14px;text-transform:uppercase}.preset-list{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}.preset-list button{border:1px solid var(--color-border,#444);padding:9px;font-size:11px}.preset-swatches{display:flex;margin-bottom:5px}.preset-swatches i{width:18px;height:14px}.color-choice{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid var(--color-border,#444);font-size:13px}.color-choice small{display:block;font:10px monospace;opacity:.65;margin-top:4px}.color-choice input{width:60px;height:38px;cursor:pointer;border:0;background:none}.symbol-list{display:grid;grid-template-columns:1fr 1fr;gap:8px}.symbol-list button{display:grid;justify-items:center;gap:7px;border:1px solid var(--color-border,#444);padding:9px;font-size:11px}.symbol-list svg{width:65px;height:52px}.symbol-list button[aria-pressed=true],.arrow-list button[aria-pressed=true]{border-color:#7FAFD3;box-shadow:inset 0 0 0 1px #7FAFD3;background:#7FAFD311}.arrow-list{display:grid;gap:8px}.arrow-list button{display:flex;align-items:center;gap:14px;padding:8px 12px;border:1px solid var(--color-border,#444);font-size:12px}.arrow-list span{width:34px;height:34px;background:#7FAFD3;font-size:24px;color:#0A0D12}.arrow-list .bold-white{font-weight:900;color:#fff;font-size:30px}.studio-actions{display:grid;gap:16px;justify-items:start}.studio-proof{min-width:0;align-self:start;position:sticky;top:90px}.preview-scroll{overflow-x:auto;border-radius:8px;padding-bottom:10px}.proof-caption{font:10px monospace;letter-spacing:1px;margin:18px 0}.studio-proof p{font-size:13px;line-height:1.7}.studio-proof .proof-note{font-size:11px;opacity:.65;margin:14px 0}.studio-process{border-top:1px solid var(--color-border,#444);padding-top:20px;margin-top:20px}.profile-links{display:flex;gap:20px;flex-wrap:wrap;border-top:1px solid var(--color-border,#444);margin-top:30px;padding-top:20px;font-size:12px}@media(max-width:900px){.studio-grid{grid-template-columns:1fr}.studio-proof{position:static;grid-row:1}.studio-controls{display:grid;grid-template-columns:1fr 1fr;gap:20px}.studio-actions{grid-column:1/-1}}@media(max-width:540px){.studio-controls{display:block}.keycap-studio{padding:18px;margin:2rem 0}.studio-proof p{font-size:12px}}
</style>
