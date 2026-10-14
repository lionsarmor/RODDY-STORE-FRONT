import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {setActivePinia,createPinia} from 'pinia';
import {useCartStore} from './stores/cart.js';
import {KEYCAP_PREVIEWS,MARKS,ARROWS,availableMarks,defaultDesign,generatePreview,designKey,designError} from './keycaps.js';
import {normalizeCatalog,validateCatalog} from './catalog-model.js';
import {cartLineKey} from './merch.js';
import {reactive} from 'vue';
import {PALETTE,colorHex,legendColorId} from './keycap-palette.js';
const catalog=normalizeCatalog(JSON.parse(readFileSync(new URL('../public/data/products.json',import.meta.url))));
const profile=catalog.keycapProfiles[0];const template=KEYCAP_PREVIEWS[profile.templateId];
test('restored X16 butterfly is selectable and profile checkboxes can hide it',()=>{
  assert.ok(MARKS['commander-x16']);
  const selected={...defaultDesign(profile),mark:'commander-x16'};
  assert.deepEqual(generatePreview(profile,selected).keys.find(k=>k.id==='commander').shapes,template.marks['commander-x16']);
  const hidden={...profile,marks:profile.marks.filter(id=>id!=='commander-x16'),defaults:{...profile.defaults,mark:'commander-x16'}};
  assert.equal(defaultDesign(hidden).mark,'roddy-r');
  assert.ok(!availableMarks(hidden).includes('commander-x16'));
  assert.ok(designError(selected,hidden));
  assert.ok(normalizeCatalog({...catalog,keycapProfiles:[profile]}).keycapProfiles[0].marks.includes('commander-x16'));
  for(const mark of ['roddy-x','pixel-rainbow-x']){
    const stale={...profile,marks:[...profile.marks,mark],defaults:{...profile.defaults,mark}};
    assert.equal(defaultDesign(stale).mark,'roddy-r');
    assert.ok(!availableMarks(stale).includes(mark));
    assert.throws(()=>generatePreview(stale,{...defaultDesign(stale),mark}));
    assert.ok(!normalizeCatalog({...catalog,keycapProfiles:[stale]}).keycapProfiles[0].marks.includes(mark));
  }
});
test('Delete uses outlined navigation lettering and Analog X is available in the preview',()=>{
  assert.ok(MARKS['analog-x']);
  const out=generatePreview(profile,{...defaultDesign(profile),mark:'analog-x'});
  assert.ok(out.keys.some(k=>k.label==='delete' && k.shapes.length===1));
  assert.ok(!out.keys.some(k=>k.label==='del'));
  assert.equal(out.keys.find((k,i)=>template.keys[i].commander).shapes.length,6);
});
test('customer preview retains all 87 v6 key appearances without manufacturing fields',()=>{
  const out=generatePreview(profile,defaultDesign(profile));
  assert.equal(out.keys.length,87);
  assert.equal(out.keys.find(k=>k.label==='esc').color,colorHex('BL003'));
  assert.deepEqual(out.keys.map(k=>k.shapes),template.keys.map(k=>k.shapes));
  const serialized=JSON.stringify(template);
  for(const field of ['keycapProfileId','layoutKeys','keyTemplates','vectDef','vectScale','vectViewbox','sourceSha256','designUrl'])assert.ok(!serialized.includes('"'+field+'"'),field+' must stay out of customer assets');
});
test('preview choices preserve PETSCII artwork and fixed swatches for every symbol and arrow combination',()=>{
  for(const mark of Object.keys(MARKS))for(const arrows of Object.keys(ARROWS)){
    const out=generatePreview(profile,{...defaultDesign(profile),mark,arrows,alpha:'YW026',modifiers:'GR001',accents:'OG001'});
    assert.equal(out.keys.length,87);
    assert.deepEqual(out.keys.find((k,i)=>template.keys[i].commander).shapes,template.marks[mark]);
    out.keys.forEach((key,i)=>{
      if(template.keys[i].commander || template.keys[i].boldArrows)return;
      assert.deepEqual(key.shapes.map(s=>s.path),template.keys[i].shapes.map(s=>s.path));
      const fixed=shapes=>shapes.filter(s=>s.inkRole!=='auto').map(s=>s.fill);
      assert.deepEqual(fixed(key.shapes),fixed(template.keys[i].shapes));
    });
  }
});
test('cart persists two designs separately and quantity/removal touches only the selected design',()=>{
  const saved=new Map();globalThis.localStorage={getItem:k=>saved.get(k),setItem:(k,v)=>saved.set(k,v)};
  setActivePinia(createPinia());const cart=useCartStore();cart.clear();
  const a=defaultDesign(profile),b={...a,mark:'analog-x'};
  cart.add('x16-keycaps',1,99,'',a);cart.add('x16-keycaps',2,99,'',b);cart.add('x16-keycaps',1,99,'',{...a});
  assert.equal(cart.items.length,2);assert.equal(cart.items[0].qty,2);assert.notEqual(cartLineKey('x16-keycaps','',a),cartLineKey('x16-keycaps','',b));
  cart.setQty('x16-keycaps',3,'',b);cart.remove('x16-keycaps','',a);assert.equal(cart.items.length,1);assert.equal(cart.items[0].qty,3);assert.equal(cart.items[0].design.mark,'analog-x');
  assert.equal(JSON.parse(saved.get('roddy:cart'))[0].design.mark,'analog-x');
});
test('all four arrow choices preserve their size and use the selected stock ink',()=>{
  const before=JSON.stringify(template);
  assert.deepEqual(profile.arrows,Object.keys(ARROWS));
  for(const arrows of profile.arrows){
    const out=generatePreview(profile,{...defaultDesign(profile),arrows});
    for(const source of template.keys.filter(k=>k.boldArrows)){
      const actual=out.keys.find(k=>k.id===source.id).shapes;
      assert.deepEqual(actual.map(s=>s.path),(arrows.startsWith('bold-')?source.boldArrows:source.shapes).map(s=>s.path));
      const ink=arrows.endsWith('-white')?'GR002':'GR001';
      assert.ok(actual.every(s=>s.paletteId===ink && s.fill===colorHex(ink)));
    }
  }
  assert.equal(JSON.stringify(template),before);
  assert.equal(template.keys.find(k=>k.id==='2').shapes[2].paletteId,'GN037');
  assert.equal(template.keys.find(k=>k.id==='7').shapes[1].paletteId,'BL026');
});
test('profiles and revisions reject stale designs and invalid publishing settings',()=>{
  const stale={...defaultDesign(profile),revision:'old'};assert.ok(designError(stale,profile));
  assert.throws(()=>generatePreview(profile,{...defaultDesign(profile),mark:'plain-x'}));
  const c=structuredClone(catalog);c.keycapProfiles[0].templateId='imaginary';assert.ok(validateCatalog(c).some(e=>e.includes('template')));
  c.keycapProfiles[0]=structuredClone(profile);c.products.find(p=>p.keycaps).trackStock=true;assert.ok(validateCatalog(c).some(e=>e.includes('made-to-order')));
});

test('individual palette colors override their groups and lettering keeps contrast',()=>{
  const design={...defaultDesign(profile),keyColors:{a:'GR001',esc:'RD003'}};
  const out=generatePreview(profile,design);
  assert.equal(out.keys.find(k=>k.id==='esc').color,colorHex('RD003'));
  assert.equal(out.keys.find(k=>k.id==='a').color,colorHex('GR001'));
  assert.ok(out.keys.find(k=>k.id==='a').shapes.filter(s=>s.inkRole==='auto').every(s=>s.fill===colorHex('GR002')));
  assert.equal(out.keys.find(k=>k.id==='b').color,colorHex(design.alpha));
  for(const key of out.keys){assert.ok(PALETTE[key.paletteId]);assert.ok(key.shapes.every(s=>Object.values(PALETTE).some(c=>c.hex===s.fill)));}
});
test('palette IDs and keys belonging to this layout are required',()=>{
  for(const changes of [{alpha:'#FAF7F0'},{accents:'ZZ999'},{keyColors:{a:'#262626'}},{keyColors:{unknown:'GR001'}},{keyColors:[]},{keyColors:null}]){
    assert.ok(designError({...defaultDesign(profile),...changes},profile));
  }
});
test('per-key designs have stable cart identities and persist separately',()=>{
  const a={...defaultDesign(profile),keyColors:{a:'RD003',esc:'GR001'}};
  const b={...defaultDesign(profile),keyColors:{esc:'GR001',a:'RD003'}};
  const c={...a,keyColors:{...a.keyColors,a:'OG001'}};
  assert.equal(designKey(a),designKey(b));assert.notEqual(designKey(a),designKey(c));
  const saved=new Map();globalThis.localStorage={getItem:k=>saved.get(k),setItem:(k,v)=>saved.set(k,v)};
  setActivePinia(createPinia());const cart=useCartStore();cart.clear();cart.add('x16-keycaps',1,99,'',a);cart.add('x16-keycaps',1,99,'',b);cart.add('x16-keycaps',1,99,'',c);
  assert.equal(cart.items.length,2);assert.equal(cart.items[0].qty,2);
  setActivePinia(createPinia());const restored=useCartStore();assert.deepEqual(restored.items[1].design.keyColors,c.keyColors);
});

test('reactive catalog defaults produce an independent per-key selection',()=>{
  const source=reactive({...profile,defaults:{...profile.defaults,keyColors:{esc:'RD003'}}});
  const design=defaultDesign(source);design.keyColors.esc='OG001';
  assert.equal(source.defaults.keyColors.esc,'RD003');
});

test('number-row text replaces boxes, adapts to individual key colors and creates distinct cart designs',()=>{
  const base=defaultDesign(profile),text={...base,numberRow:'text',keyColors:{'1':'GR001'}};
  const before=JSON.stringify(template);const out=generatePreview(profile,text);
  for(const key of out.keys){
    const source=template.keys.find(k=>k.id===key.id);
    if(source.numberRowText){
      assert.deepEqual(key.shapes.map(s=>s.path),source.numberRowText.map(s=>s.path));
      assert.ok(key.shapes.every(s=>s.fill===colorHex(legendColorId(key.paletteId))));
      assert.ok(!key.shapes.some(s=>source.shapes.slice(1).some(box=>box.path===s.path)));
    }else assert.deepEqual(key.shapes,generatePreview(profile,base).keys.find(k=>k.id===key.id).shapes);
  }
  assert.equal(out.keys.filter(k=>template.keys.find(s=>s.id===k.id).numberRowText).length,8);
  assert.equal(JSON.stringify(template),before);
  assert.notEqual(designKey(base),designKey({...base,numberRow:'text'}));
  assert.ok(designError({...base,numberRow:'unknown'},profile));
  assert.ok(designError(text,{...profile,numberRows:['swatches']}));
  const saved=new Map();globalThis.localStorage={getItem:k=>saved.get(k),setItem:(k,v)=>saved.set(k,v)};
  setActivePinia(createPinia());const cart=useCartStore();cart.clear();cart.add('x16-keycaps',1,99,'',base);cart.add('x16-keycaps',1,99,'',text);
  assert.equal(cart.items.length,2);assert.equal(JSON.parse(saved.get('roddy:cart'))[1].design.numberRow,'text');
});
