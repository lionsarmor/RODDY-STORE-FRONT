import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {setActivePinia,createPinia} from 'pinia';
import {useCartStore} from './stores/cart.js';
import {KEYCAP_TEMPLATES,MARKS,ARROWS,defaultDesign,generateDesign,designKey,designError} from './keycaps.js';
import {normalizeCatalog,validateCatalog} from './catalog-model.js';
import {cartLineKey} from './merch.js';
const catalog=normalizeCatalog(JSON.parse(readFileSync(new URL('../public/data/products.json',import.meta.url))));
const profile=catalog.keycapProfiles[0];const template=KEYCAP_TEMPLATES[profile.templateId];
test('default design preserves all 87 v6 keys, vectors, swatches, blue Esc and the original Commander mark',()=>{
  const out=generateDesign(profile,defaultDesign(profile));
  assert.equal(out.layoutKeys.length,87);assert.deepEqual(out.layoutKeys,template.base.layoutKeys);assert.deepEqual(out.keyTemplates,template.base.keyTemplates);
  assert.deepEqual(out.keys,template.base.keys);
  const esc=out.layoutKeys.find(k=>k.labelId==='esc');assert.equal(out.keys[esc.id].colorId,'#7FAFD3');
});
test('every symbol and arrow combination exports embedded vectors without altering PETSCII and numbered swatches',()=>{
  for(const mark of Object.keys(MARKS))for(const arrows of Object.keys(ARROWS)){
    const out=generateDesign(profile,{...defaultDesign(profile),mark,arrows,alpha:'#FFFFFF',modifiers:'#111111',accents:'#E6B24C'});
    assert.equal(out.layoutKeys.length,87);assert.equal(out.keys.md4RrQ.layers.length,template.marks[mark].length);
    for(const k of out.layoutKeys){
      if(!['arrow-up','arrow-down','arrow-left','arrow-right','super'].includes(k.labelId)){
        assert.deepEqual(out.keys[k.id].layers.map(l=>l.vectDef),template.base.keys[k.id].layers.map(l=>l.vectDef));
        const originalColors=template.base.keys[k.id].layers.filter(l=>!['#0A0D12','#F7F7F5'].includes(l.colorId)).map(l=>l.colorId);
        assert.deepEqual(out.keys[k.id].layers.filter(l=>!['#0A0D12','#F7F7F5'].includes(l.colorId)).map(l=>l.colorId),originalColors);
      }
      assert.ok(out.keys[k.id].layers.every(l=>l.vectDef&&!l.vectId&&!l.vectCollectionId));
    }
  }
});
test('cart persists two designs separately and quantity/removal touches only the selected design',()=>{
  const saved=new Map();globalThis.localStorage={getItem:k=>saved.get(k),setItem:(k,v)=>saved.set(k,v)};
  setActivePinia(createPinia());const cart=useCartStore();cart.clear();
  const a=defaultDesign(profile),b={...a,mark:'roddy-x'};
  cart.add('x16-keycaps',1,99,'',a);cart.add('x16-keycaps',2,99,'',b);cart.add('x16-keycaps',1,99,'',{...a});
  assert.equal(cart.items.length,2);assert.equal(cart.items[0].qty,2);assert.notEqual(cartLineKey('x16-keycaps','',a),cartLineKey('x16-keycaps','',b));
  cart.setQty('x16-keycaps',3,'',b);cart.remove('x16-keycaps','',a);assert.equal(cart.items.length,1);assert.equal(cart.items[0].qty,3);assert.equal(cart.items[0].design.mark,'roddy-x');
  assert.equal(JSON.parse(saved.get('roddy:cart'))[0].design.mark,'roddy-x');
});
test('profiles and revisions reject stale designs and invalid publishing settings',()=>{
  const stale={...defaultDesign(profile),revision:'old'};assert.ok(designError(stale,profile));
  assert.throws(()=>generateDesign(profile,{...defaultDesign(profile),mark:'plain-x'}));
  const c=structuredClone(catalog);c.keycapProfiles[0].templateId='imaginary';assert.ok(validateCatalog(c).some(e=>e.includes('template')));
  c.keycapProfiles[0]=structuredClone(profile);c.products.find(p=>p.keycaps).trackStock=true;assert.ok(validateCatalog(c).some(e=>e.includes('made-to-order')));
});
