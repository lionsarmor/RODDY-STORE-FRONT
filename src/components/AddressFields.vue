<script setup>
defineProps({address:{type:Object,required:true}});
</script>
<template>
  <div class="address-fields">
    <label>First name<input v-model="address.first_name" autocomplete="given-name" maxlength="80" required /></label>
    <label>Last name<input v-model="address.last_name" autocomplete="family-name" maxlength="80" required /></label>
    <label class="wide">Email<input v-model="address.email" type="email" autocomplete="email" maxlength="254" required /></label>
    <label class="wide">Phone<input v-model="address.phone" type="tel" autocomplete="tel" maxlength="30" required /></label>
    <label class="wide">Address<input v-model="address.address1" autocomplete="address-line1" maxlength="150" required /></label>
    <label class="wide">Apartment / suite (optional)<input v-model="address.address2" autocomplete="address-line2" maxlength="150" /></label>
    <label class="wide">City<input v-model="address.city" autocomplete="address-level2" maxlength="100" required /></label>
    <label>Country<select v-model="address.country" autocomplete="country"><option value="US">United States</option><option value="CA">Canada</option></select></label>
    <label>State / province code<input v-model="address.region" autocomplete="address-level1" placeholder="CA / ON" minlength="2" maxlength="2" required /></label>
    <label class="wide">ZIP / postal code<input v-model="address.zip" autocomplete="postal-code" maxlength="12" required /></label>
  </div>
</template>
<style scoped>
.address-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.address-fields label{display:grid;gap:6px;min-width:0;font-size:13px}.wide{grid-column:1/-1}.address-fields input,.address-fields select{width:100%;min-width:0;background:var(--color-panel);color:inherit;border:1px solid var(--color-border);padding:11px;font:inherit;border-radius:4px}
</style>
