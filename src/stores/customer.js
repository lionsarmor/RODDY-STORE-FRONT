import {defineStore} from 'pinia';
import {useCatalogStore} from './catalog';
import {CUSTOMER_SESSION_KEY, customerRequest} from '../customer-api.js';
let listening=false;

export const useCustomerStore = defineStore('customer', {
  state: () => ({session:null, profile:null, loading:false, generation:0}),
  getters: {
    signedIn: state => Boolean(state.session && state.profile),
    addresses: state => state.profile?.addresses || [],
  },
  actions: {
    remember(session) {
      this.generation++;
      this.session=session;
      this.profile=null;
      try { if (session) localStorage.setItem(CUSTOMER_SESSION_KEY, JSON.stringify(session)); else localStorage.removeItem(CUSTOMER_SESSION_KEY); } catch {}
    },
    async request(path, body) {
      return customerRequest(useCatalogStore().settings.checkoutEndpoint, path, this.session?.token || '', body);
    },
    async load() {
      if(!listening){listening=true;window.addEventListener('storage',event=>{if(event.key===CUSTOMER_SESSION_KEY || event.key===null){this.generation++;this.session=null;this.profile=null;this.load().catch(()=>{});}});}
      try {
        const saved=JSON.parse(localStorage.getItem(CUSTOMER_SESSION_KEY) || 'null');
        const current=saved?.expiresAt > Date.now()/1000 ? saved : null;
        if(current?.token!==this.session?.token){this.generation++;this.profile=null;this.session=current;}
      } catch { /* An in-memory sign-in still works with storage disabled. */ }
      if (!this.session) {this.profile=null;return;}
      const generation=this.generation, token=this.session.token;
      this.loading=true;
      try {
        const profile=await this.request('/customer/me');
        if (generation===this.generation && token===this.session?.token) this.profile=profile;
      } catch (error) {
        if (generation===this.generation) {this.profile=null;if(error.status===401)this.remember(null);}
        throw error;
      } finally {this.loading=false;}
    },
    async authenticate(mode, credentials) {
      const session=await customerRequest(useCatalogStore().settings.checkoutEndpoint, '/forum/'+mode, '', credentials);
      this.remember(session);await this.load();
    },
    async saveProfile(profile) {
      const token=this.session?.token;
      const result=await this.request('/customer/me',profile);
      if(token!==this.session?.token)throw new Error('Your account changed. Sign in again.');
      this.profile=result;
    },
    async saveAddress(entry) {
      const token=this.session?.token;
      const result=await this.request('/customer/addresses',entry);
      if(token!==this.session?.token || !this.profile)throw new Error('Your account changed. Sign in again.');
      this.profile.addresses=result.addresses;return result.id;
    },
    async deleteAddress(id) {
      const token=this.session?.token;
      const result=await this.request('/customer/addresses/'+encodeURIComponent(id)+'/delete',{});
      if(token!==this.session?.token || !this.profile)throw new Error('Your account changed. Sign in again.');
      this.profile.addresses=result.addresses;
    },
    async logout() {
      // Revocation must succeed before claiming the session has been signed out.
      if(this.session) await this.request('/forum/logout',{});
      this.remember(null);
    },
  },
});
