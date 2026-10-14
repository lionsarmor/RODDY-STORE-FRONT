import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {setActivePinia,createPinia} from 'pinia';
import {useCartStore} from './stores/cart.js';
import {KEYCAP_PREVIEWS,MARKS,ARROWS,defaultDesign,generatePreview,designKey,designError} from './keycaps.js';
import {normalizeCatalog,validateCatalog} from './catalog-model.js';
import {cartLineKey} from './merch.js';
const catalog=normalizeCatalog(JSON.parse(readFileSync(new URL('../public/data/products.json',import.meta.url))));
const profile=catalog.keycapProfiles[0];const template=KEYCAP_PREVIEWS[profile.templateId];
test('customer preview retains all 87 v6 key appearances without Yuzu manufacturing fields',()=>{
  const out=generatePreview(profile,defaultDesign(profile));
  assert.equal(out.keys.length,87);
  assert.equal(out.keys.find(k=>k.label==='esc').color,'#7FAFD3');
  assert.deepEqual(out.keys.map(k=>k.shapes),template.keys.map(k=>k.shapes));
  const serialized=JSON.stringify(template);
  for(const field of ['keycapProfileId','layoutKeys','keyTemplates','vectDef','vectScale','vectViewbox','sourceSha256','designUrl'])assert.ok(!serialized.includes('"'+field+'"'),field+' must stay out of customer assets');
});
test('preview choices preserve PETSCII artwork and fixed swatches for every symbol and arrow combination',()=>{
  for(const mark of Object.keys(MARKS))for(const arrows of Object.keys(ARROWS)){
    const out=generatePreview(profile,{...defaultDesign(profile),mark,arrows,alpha:'#FFFFFF',modifiers:'#111111',accents:'#E6B24C'});
    assert.equal(out.keys.length,87);
    assert.deepEqual(out.keys.find((k,i)=>template.keys[i].commander).shapes,template.marks[mark]);
    out.keys.forEach((key,i)=>{
      if(template.keys[i].commander || template.keys[i].boldArrows)return;
      assert.deepEqual(key.shapes.map(s=>s.path),template.keys[i].shapes.map(s=>s.path));
      const fixed=shapes=>shapes.filter(s=>!['#0A0D12','#F7F7F5'].includes(s.fill)).map(s=>s.fill);
      assert.deepEqual(fixed(key.shapes),fixed(template.keys[i].shapes));
    });
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
  assert.throws(()=>generatePreview(profile,{...defaultDesign(profile),mark:'plain-x'}));
  const c=structuredClone(catalog);c.keycapProfiles[0].templateId='imaginary';assert.ok(validateCatalog(c).some(e=>e.includes('template')));
  c.keycapProfiles[0]=structuredClone(profile);c.products.find(p=>p.keycaps).trackStock=true;assert.ok(validateCatalog(c).some(e=>e.includes('made-to-order')));
});
