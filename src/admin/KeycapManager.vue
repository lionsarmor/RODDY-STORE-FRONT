<script setup>
import {computed} from 'vue';
import PaletteColorPicker from '../components/PaletteColorPicker.vue';
import {KEYCAP_PREVIEWS,MARKS,availableMarks,ARROWS,NUMBER_ROWS,DEFAULT_SELECTION} from '../keycaps.js';
import {normalizeProduct} from '../catalog-model';
const props=defineProps({catalog:Object,endpoint:String,token:String,connected:Boolean});
const emit=defineEmits(['edit-product','open-orders']);
const profiles=computed(()=>props.catalog.keycapProfiles);
function slug(name){return name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'') || 'keyboard';}
function unique(base,list){let id=base,n=2;while(list.some(x=>x.id===id))id=base+'-'+n++;return id;}
function addProfile(source=null){
  const p=source?structuredClone(JSON.parse(JSON.stringify(source))):{name:'New keyboard set',revision:'1',templateId:Object.keys(KEYCAP_PREVIEWS)[0],description:'',marks:Object.keys(MARKS),arrows:Object.keys(ARROWS),numberRows:[...(Object.values(KEYCAP_PREVIEWS)[0].numberRows || ['swatches','text'])],defaults:{...DEFAULT_SELECTION}};
  if(source)p.name+=' copy';p.id=unique(slug(p.name),profiles.value);profiles.value.push(p);
}
function productsFor(profile){return props.catalog.products.filter(p=>p.keycaps?.profileId===profile.id);}
function changeTemplate(profile){const modes=KEYCAP_PREVIEWS[profile.templateId]?.numberRows || [];profile.numberRows=profile.numberRows.filter(id=>modes.includes(id));if(!profile.numberRows.length)profile.numberRows=[...modes];if(!profile.numberRows.includes(profile.defaults.numberRow))profile.defaults.numberRow=profile.numberRows[0];}
function createProduct(profile){
  const id=unique(profile.id+'-keycaps',props.catalog.products);
  const p=normalizeProduct({id,sku:'KCAP-'+id.toUpperCase(),name:profile.name+' keycaps',category:props.catalog.categories.find(c=>c.id==='labs')?.id || props.catalog.categories[0]?.id || '',active:false,featured:false,status:'coming-soon',type:'physical',price:0,pricePending:true,stock:0,trackStock:false,description:profile.description,shortDescription:profile.description.slice(0,160),keycaps:{profileId:profile.id},coverImage:'img/keycaps/x16-v06.svg',images:['img/keycaps/x16-v06.svg'],tags:[],specs:{},releaseNote:'Design your set now. Ordering opens once manufacturing, pricing and shipping are confirmed.'});
  props.catalog.products.unshift(p);emit('edit-product',p);
}
function toggle(profile,field,id,checked){const list=profile[field];if(checked&&!list.includes(id))list.push(id);if(!checked)profile[field]=list.filter(x=>x!==id);const choice={marks:'mark',arrows:'arrows',numberRows:'numberRow'}[field];if(!profile[field].includes(profile.defaults[choice]))profile.defaults[choice]=profile[field][0] || '';}
</script>
<template>
  <section>
    <div class="section-heading"><div><h2>Keyboard profiles & custom sets</h2><p class="help-copy">A keyboard profile defines the layout, artwork, available symbols and default colors. Each product points to one profile and has its own page, price and shipping. Profile edits and new pages publish with your catalog draft.</p></div><button class="button primary small" @click="addProfile()">Add keyboard profile +</button></div>
    <p class="notice">Start with the validated v6 ANSI 87-key Cherry layout. Duplicate it for other color or symbol collections. A different physical layout needs its own validated template before it appears in this menu; renaming a profile does not change key sizes or fit.</p>
    <article v-for="profile in profiles" :key="profile.id" class="profile-editor">
      <div class="field-heading"><h3>{{profile.name}}</h3><button class="button small" @click="addProfile(profile)">Duplicate profile</button></div>
      <div class="form-grid"><label>Profile name<input v-model="profile.name" maxlength="120" /></label><label>Stable profile ID<input :value="profile.id" readonly /></label><label>Design revision<input v-model="profile.revision" maxlength="40" /><small>Change this when updating artwork or available choices. Saved carts must refresh; paid orders retain their original files.</small></label><label>Physical template<select v-model="profile.templateId" @change="changeTemplate(profile)"><option v-for="template in KEYCAP_PREVIEWS" :key="template.id" :value="template.id">{{template.name}}</option></select></label><label class="full">Profile description<textarea v-model="profile.description" rows="2" /></label></div>
      <p class="help-copy">{{KEYCAP_PREVIEWS[profile.templateId]?.compatibility}}</p>
      <div class="form-grid"><fieldset><legend>Available Commander symbols</legend><label v-for="(name,id) in MARKS" :key="id" class="check"><input type="checkbox" :checked="profile.marks.includes(id)" @change="toggle(profile,'marks',id,$event.target.checked)" />{{name}}</label></fieldset><fieldset><legend>Available arrows</legend><label v-for="(name,id) in ARROWS" :key="id" class="check"><input type="checkbox" :checked="profile.arrows.includes(id)" @change="toggle(profile,'arrows',id,$event.target.checked)" />{{name}}</label></fieldset></div>
      <fieldset><legend>Available number-row legends</legend><label v-for="(name,id) in Object.fromEntries((KEYCAP_PREVIEWS[profile.templateId]?.numberRows || []).map(id=>[id,NUMBER_ROWS[id]]))" :key="id" class="check"><input type="checkbox" :checked="profile.numberRows.includes(id)" @change="toggle(profile,'numberRows',id,$event.target.checked)" />{{name}}</label></fieldset>
      <h4>Starting design</h4><div class="form-grid"><PaletteColorPicker v-for="[id,name] in [['alpha','Main keys'],['modifiers','Modifiers'],['accents','Accent keys']]" :key="id" v-model="profile.defaults[id]" :label="name" /><label>Default symbol<select v-model="profile.defaults.mark"><option v-for="id in availableMarks(profile)" :key="id" :value="id">{{MARKS[id]}}</option></select></label><label>Default number-row legends<select v-model="profile.defaults.numberRow"><option v-for="id in profile.numberRows" :key="id" :value="id">{{NUMBER_ROWS[id]}}</option></select></label><label>Default arrows<select v-model="profile.defaults.arrows"><option v-for="id in profile.arrows" :key="id" :value="id">{{ARROWS[id]}}</option></select></label></div>
      <div class="admin-actions"><button class="button small" @click="createProduct(profile)">Create product page for this profile +</button><button v-for="product in productsFor(profile)" :key="product.id" class="button small" @click="$emit('edit-product',product)">Edit {{product.name}}</button><button v-if="!productsFor(profile).length" class="text-button" @click="catalog.keycapProfiles=catalog.keycapProfiles.filter(p=>p!==profile)">Remove unused profile</button></div>
      <p class="help-copy">New product pages start hidden and coming soon. Set the retail price, supported-country shipping rates and availability in the product editor. Publish when ready. Custom keycaps are submitted to the maker manually after payment.</p>
    </article>
    <p class="help-copy">Ready to process an order? <button class="text-button" @click="$emit('open-orders')">Manage all orders ↗</button></p>
  </section>
</template>
<style scoped>.profile-editor{border:1px solid var(--color-border,#444);padding:24px;margin:24px 0}.profile-editor h4{margin:20px 0 12px}.profile-editor fieldset{border:1px solid var(--color-border,#444);padding:14px}.profile-editor legend{font-size:12px}.profile-editor .admin-actions{margin:18px 0}.profile-editor a{text-decoration:underline}</style>
