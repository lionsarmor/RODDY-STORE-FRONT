<script setup>
import {ref,reactive,watch,onMounted,computed} from 'vue';
import {useRoute,useRouter} from 'vue-router';
import {useCustomerStore} from '../stores/customer';
import {useCatalogStore} from '../stores/catalog';
import {emptyAddress,customerRequest} from '../customer-api';
import AddressFields from '../components/AddressFields.vue';
import RoddyLogo from '../components/RoddyLogo.vue';
const customer=useCustomerStore(),catalog=useCatalogStore(),route=useRoute(),router=useRouter();
const returnTo=computed(()=>route.query.return==='cart'?'/cart':route.query.return==='community'?{path:'/contact',query:{board:'1',...(/^[1-9][0-9]{0,14}$/.test(route.query.topic || '')?{topic:route.query.topic}:route.query.compose==='1'?{compose:'1'}:{})}}:'/shop');
function finishAuthentication(){recoveryCode.value='';if(['cart','community'].includes(route.query.return))router.replace(returnTo.value);}
const mode=ref('login'),busy=ref(false),error=ref(''),notice=ref(''),recoveryCode=ref('');
const login=reactive({handle:'',password:'',name:'',email:'',recoveryCode:'',newPassword:''});
const profile=reactive({name:'',email:''});
const editor=ref(false),deleting=ref('');
const entry=reactive({id:'',label:'Home',default:false,address:emptyAddress()});
const security=reactive({password:'',newPassword:''});
watch(()=>customer.profile, p=>{profile.name=p?.name || '';profile.email=p?.email || '';});
async function action(fn){busy.value=true;error.value='';notice.value='';try{await fn();}catch(e){error.value=e.message;}finally{busy.value=false;}}
async function load(){if(!catalog.settings.checkoutEndpoint)return;await action(()=>customer.load());}
onMounted(load);
watch(()=>catalog.settings.checkoutEndpoint,load);
async function authenticate(){await action(async()=>{
  if(mode.value==='recover'){
    const session=await customerRequest(catalog.settings.checkoutEndpoint,'/customer/recover','',{handle:login.handle,recoveryCode:login.recoveryCode,newPassword:login.newPassword});
    customer.remember(session);await customer.load();notice.value='Password reset. Create a new recovery code below.';
  }else{
    await customer.authenticate(mode.value,{handle:login.handle,password:login.password});
    if(mode.value==='register'){
      await customer.saveProfile({name:login.name,email:login.email});
      recoveryCode.value=(await customer.request('/customer/recovery-code',{password:login.password})).recoveryCode;
      customer.profile.hasRecoveryCode=true;
      notice.value='Welcome to RODDY. Save your recovery code somewhere safe.';
    }
  }
  login.password='';login.newPassword='';login.recoveryCode='';
  if(mode.value==='login')finishAuthentication();
});}
function editAddress(existing){Object.assign(entry,{id:existing?.id || '',label:existing?.label || 'Home',default:existing?.default || !customer.addresses.length,address:{...emptyAddress(),...(existing?.address || {}),email:existing?.address?.email || customer.profile?.email || ''}});editor.value=true;deleting.value='';}
async function saveAddress(){await action(async()=>{await customer.saveAddress(entry);editor.value=false;notice.value='Address saved. It is ready for your next checkout.';});}
async function setDefault(saved){await action(async()=>{await customer.saveAddress({...saved,default:true});notice.value='Default address updated.';});}
async function removeAddress(id){await action(async()=>{await customer.deleteAddress(id);deleting.value='';notice.value='Address removed. Existing orders keep their original delivery details.';});}
async function saveProfile(){await action(async()=>{await customer.saveProfile(profile);notice.value='Your details are saved.';});}
async function generateCode(){await action(async()=>{recoveryCode.value=(await customer.request('/customer/recovery-code',{password:security.password})).recoveryCode;security.password='';customer.profile.hasRecoveryCode=true;notice.value='This replaces any previous recovery code. Save it now.';});}
async function changePassword(){await action(async()=>{const session=await customer.request('/customer/password',security);customer.remember(session);await customer.load();security.password='';security.newPassword='';recoveryCode.value='';notice.value='Password updated. Other sessions are signed out. Generate a new recovery code below.';});}
async function logout(){await action(async()=>{await customer.logout();editor.value=false;recoveryCode.value='';security.password='';security.newPassword='';notice.value='You are signed out.';});}
</script>
<template>
  <article class="account-page">
    <header class="account-hero"><div><p class="eyebrow">RODDY / YOUR CORNER</p><h1>A LITTLE MORE<br />AT HOME<span>.</span></h1><p>Your details. Your addresses. A quicker next checkout.</p></div><RoddyLogo kind="badge" class="account-badge" /></header>
    <div class="account-topline"><RouterLink :to="returnTo" class="text-button">{{route.query.return==='cart'?'← Back to your cart':route.query.return==='community'?'← Back to the noticeboard':'← Keep exploring'}}</RouterLink><button v-if="customer.signedIn" class="text-button" :disabled="busy" @click="logout">Sign out</button></div>
    <p v-if="error" class="notice" role="alert">{{error}}</p><p v-if="notice" class="notice" role="status">{{notice}}</p>
    <p v-if="customer.loading" role="status">Loading your account…</p>
    <div v-if="!customer.signedIn" class="account-columns">
      <section class="account-panel"><div class="account-tabs"><button :aria-pressed="mode==='login'" @click="mode='login'">Sign in</button><button :aria-pressed="mode==='register'" @click="mode='register'">Create account</button></div>
        <h2>{{mode==='recover'?'Get back into your account.':mode==='register'?'Make yourself at home.':'Good to see you again.'}}</h2>
        <p class="account-help">Already have a RODDY community handle? Use the same handle and password here.</p>
        <form @submit.prevent="authenticate">
          <label>Handle<input v-model="login.handle" autocomplete="username" pattern="[A-Za-z0-9_]{3,24}" minlength="3" maxlength="24" required /><small>3–24 letters, numbers or underscores. This is also your public community handle.</small></label>
          <template v-if="mode==='register'"><label>Your name<input v-model="login.name" autocomplete="name" maxlength="160" required /></label><label>Contact email<input v-model="login.email" type="email" autocomplete="email" maxlength="254" required /></label></template>
          <template v-if="mode==='recover'"><label>Recovery code<input v-model="login.recoveryCode" autocomplete="off" maxlength="100" required /></label><label>New password<input v-model="login.newPassword" type="password" autocomplete="new-password" minlength="8" maxlength="128" required /></label></template>
          <label v-else>Password<input v-model="login.password" type="password" :autocomplete="mode==='register'?'new-password':'current-password'" minlength="8" maxlength="128" required /></label>
          <button class="button primary" :disabled="busy">{{busy?'One moment…':mode==='register'?'Create my account →':mode==='recover'?'Reset password →':'Sign in →'}}</button>
          <button v-if="mode==='login'" type="button" class="text-button" @click="mode='recover'">Forgot password? Use your recovery code</button>
          <p v-if="mode==='recover'" class="account-help">Use the private recovery code you saved from your account. Your contact email alone cannot reset your password.</p>
        </form>
      </section>
      <aside class="account-panel account-guest"><p class="eyebrow">JUST PASSING THROUGH?</p><h2>Guests are<br />always welcome.</h2><p>An account is optional. You can place an order without signing up.</p><RouterLink to="/cart?guest=1" class="button">Continue as guest →</RouterLink><p class="account-help">Accounts keep your shipping addresses private and ready to reuse. Payment details stay with secure checkout.</p></aside>
    </div>
    <template v-else>
      <section v-if="recoveryCode" class="account-panel recovery-panel"><h2>Keep your way back in.</h2><p>Save this single-use recovery code in your password manager. We cannot show it again after you leave.</p><code>{{recoveryCode}}</code><button class="text-button" @click="finishAuthentication">I have saved it</button></section>
      <div class="account-columns">
        <section class="account-panel"><p class="eyebrow">01 / YOUR DETAILS</p><h2>Hello, {{customer.profile.handle}}.</h2><form @submit.prevent="saveProfile"><label>Your name<input v-model="profile.name" autocomplete="name" maxlength="160" required /></label><label>Contact email<input v-model="profile.email" type="email" autocomplete="email" maxlength="254" required /></label><button class="button" :disabled="busy">Save my details</button></form><p class="account-help">Your name, email and addresses are private. Only your handle appears in the community.</p></section>
        <section class="account-panel"><p class="eyebrow">02 / YOUR ADDRESS BOOK</p><h2>Where should it go?</h2><p v-if="!customer.addresses.length">Add your first address and skip the typing next time.</p>
          <article v-for="saved in customer.addresses" :key="saved.id" class="saved-address"><div class="address-heading"><h3>{{saved.label}}</h3><span v-if="saved.default">DEFAULT</span></div><address>{{saved.address.first_name}} {{saved.address.last_name}}<br />{{saved.address.address1}}<template v-if="saved.address.address2"><br />{{saved.address.address2}}</template><br />{{saved.address.city}}, {{saved.address.region}} {{saved.address.zip}}<br />{{saved.address.country==='US'?'United States':'Canada'}}</address><div class="address-actions"><button class="text-button" :disabled="busy" @click="editAddress(saved)">Edit</button><button v-if="!saved.default" class="text-button" :disabled="busy" @click="setDefault(saved)">Make default</button><button class="text-button" :disabled="busy" @click="deleting=saved.id">Remove</button></div><p v-if="deleting===saved.id">Remove this saved address? <button class="text-button" :disabled="busy" @click="removeAddress(saved.id)">Yes, remove</button> <button class="text-button" @click="deleting=''">Keep it</button></p></article>
          <button v-if="customer.addresses.length<10" class="button" :disabled="busy" @click="editAddress()">+ Add an address</button>
          <form v-if="editor" class="address-editor" @submit.prevent="saveAddress"><h3>{{entry.id?'Edit address':'New address'}}</h3><label>Address label<input v-model="entry.label" placeholder="Home, work…" maxlength="40" required /></label><AddressFields :address="entry.address" /><label class="check-label"><input v-model="entry.default" type="checkbox" /> Use as my default address</label><div class="address-actions"><button class="button primary" :disabled="busy">Save address</button><button type="button" class="text-button" @click="editor=false">Cancel</button></div></form>
        </section>
      </div>
      <details class="account-panel security-panel"><summary>03 / Password & recovery</summary><p class="account-help">Changing your password signs out other sessions and clears your old recovery code.</p><form @submit.prevent="changePassword"><label>Current password<input v-model="security.password" type="password" autocomplete="current-password" minlength="8" maxlength="128" required /></label><label>New password<input v-model="security.newPassword" type="password" autocomplete="new-password" minlength="8" maxlength="128" required /></label><button class="button" :disabled="busy">Update password</button><button type="button" class="text-button" :disabled="busy || !security.password" @click="generateCode">{{customer.profile.hasRecoveryCode?'Replace recovery code':'Create recovery code'}} using current password</button></form></details>
    </template>
  </article>
</template>
<style scoped>
.account-page{max-width:1120px;margin:auto;padding:48px 24px 80px}.account-hero{display:flex;justify-content:space-between;align-items:center;gap:30px;border-bottom:3px solid var(--color-brand);padding-bottom:30px}.account-hero h1{font-size:clamp(34px,6vw,66px);font-weight:900;line-height:1.05;margin:16px 0;letter-spacing:-.045em}.account-hero h1 span{color:var(--color-brand)}.account-badge{width:150px;flex-shrink:0}.account-topline{display:flex;justify-content:space-between;gap:16px;margin:24px 0}.account-columns{display:grid;grid-template-columns:1fr 1.2fr;gap:24px}.account-panel{background:var(--color-panel);border:1px solid var(--color-border);padding:28px;border-radius:12px;min-width:0}.account-panel h2{overflow-wrap:anywhere;font-size:26px;font-weight:800;line-height:1.2;margin:16px 0}.account-panel p{line-height:1.65;margin:12px 0}.account-panel form{display:grid;gap:16px}.account-panel label{display:grid;gap:7px;font-size:14px}.account-panel label input:not([type=checkbox]){min-width:0;width:100%;padding:11px;border:1px solid var(--color-border);border-radius:4px;background:var(--color-bg);color:inherit}.account-help,small{font-size:12px;line-height:1.6;color:var(--color-text-dim)}.account-tabs,.address-actions{display:flex;gap:16px;flex-wrap:wrap;align-items:center}.account-tabs button{padding-bottom:10px;border-bottom:3px solid transparent}.account-tabs button[aria-pressed=true]{border-color:var(--color-brand);font-weight:800}.account-guest{border-top:5px solid var(--color-brand)}.account-guest h2{font-size:38px}.saved-address{padding:18px 0;border-bottom:1px solid var(--color-border);margin-bottom:20px}.address-heading{display:flex;justify-content:space-between;align-items:center;gap:10px}.address-heading h3{font-weight:800}.address-heading span{font:10px monospace;border:1px solid var(--color-border);padding:4px 8px}.saved-address address{font-style:normal;font-size:14px;line-height:1.7;margin:12px 0}.address-editor{margin-top:24px;padding-top:20px;border-top:2px solid var(--color-brand)}.account-panel .check-label{display:flex;align-items:center}.security-panel,.recovery-panel{margin:24px 0}.security-panel summary{cursor:pointer;font-weight:800}.security-panel form{max-width:500px}.recovery-panel{border:2px solid var(--color-brand)}.recovery-panel code{display:block;overflow-wrap:anywhere;background:var(--color-bg);padding:16px;margin:16px 0;font-size:16px}@media(max-width:700px){.account-columns{grid-template-columns:1fr}.account-badge{width:86px}.account-page{padding:28px 16px 60px}.account-panel{padding:22px}.account-hero{gap:14px}}
</style>
