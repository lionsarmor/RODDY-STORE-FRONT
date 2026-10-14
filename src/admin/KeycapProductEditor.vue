<script setup>
import OfficeShipping from "./OfficeShipping.vue";
const props=defineProps({product:Object,catalog:Object});
function select(id){props.product.keycaps=id?{profileId:id}:null;if(id){props.product.trackStock=false;props.product.merch=null;props.product.supplier=null;}}

</script>
<template>
  <section><h3>Custom keyboard set</h3><label>Keyboard profile<select :value="product.keycaps?.profileId || ''" @change="select($event.target.value)"><option value="">No custom keycap designer</option><option v-for="profile in catalog.keycapProfiles" :key="profile.id" :value="profile.id">{{profile.name}} · {{profile.revision}}</option></select></label>
    <template v-if="product.keycaps"><p class="help-copy">This page uses the selected profile's artwork and choices. Manage profiles in Keycap profiles. After verified payment, the droplet saves the exact design JSON and delivery details for download for you to place the maker order manually.</p><OfficeShipping :product="product" /><p class="notice">Launch checklist: approved physical sample, final retail price, confirmed shipping and production times, working order packet downloads. Then turn off pricing pending, choose Available and publish. Stock tracking stays off for these made-to-order sets.</p></template>
  </section>
</template>
