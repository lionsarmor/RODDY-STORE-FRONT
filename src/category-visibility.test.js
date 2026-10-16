import test from 'node:test';
import assert from 'node:assert/strict';
import {categoryVisible, visibleProducts, categoryPreviewUrl} from './category-visibility.js';
import {normalizeCatalog, validateCatalog} from './catalog-model.js';
import {readFileSync} from 'node:fs';
const key='kits-preview-1234567890';
const categories=[{id:'labs',name:'Labs'},{id:'kits',name:'Kits',visible:false,previewKey:key},{id:'future',name:'Future',visible:false,previewKey:'other-preview-1234567890'}];
const products=[{id:'main',active:true,category:'labs'},{id:'kit',active:true,category:'kits'},{id:'disabled',active:false,category:'kits'},{id:'other',active:true,category:'future'}];
test('public browsing excludes hidden-category products even if active or featured',()=>{
 assert.deepEqual(visibleProducts(products,categories).map(p=>p.id),['main']);
 assert.deepEqual(visibleProducts(products,categories,'wrong-link').map(p=>p.id),['main']);
});
test('preview reveals one category, never inactive products or another hidden category',()=>{
 assert.deepEqual(visibleProducts(products,categories,key).map(p=>p.id),['main','kit']);
 assert.equal(categoryVisible(categories[2],key),false);
 assert.equal(categoryVisible({visible:false},''),false);
});
test('visibility toggle and link rotation take effect without editing products',()=>{
 const c=structuredClone(categories);c[1].visible=true;
 assert.deepEqual(visibleProducts(products,c).map(p=>p.id),['main','kit']);
 c[1].visible=false;c[1].previewKey='replacement-1234567890';
 assert.deepEqual(visibleProducts(products,c,key).map(p=>p.id),['main']);
});
test('admin draft preview can see hidden categories; share link never enables draft mode',()=>{
 assert.deepEqual(visibleProducts(products,categories,'',true).map(p=>p.id),['main','kit','other']);
 const url=new URL(categoryPreviewUrl('https://roddy.world/admin.html?preview=1#/settings',categories[1]));
 assert.equal(url.pathname,'/');assert.equal(url.searchParams.get('category-preview'),key);assert.equal(url.searchParams.has('preview'),false);assert.equal(url.hash,'#/shop?cat=kits');
 const publicUrl=new URL(categoryPreviewUrl(url.href,categories[0]));assert.equal(publicUrl.search,'');
});
test('catalog round-trip preserves keys and requires distinct usable hidden-category links',()=>{
 const catalog=normalizeCatalog(JSON.parse(readFileSync('public/data/products.json')));
 assert.equal(validateCatalog(catalog).length,0);
 const kits=catalog.categories.find(c=>c.id==='kits');assert.equal(kits.visible,false);
 assert.equal(normalizeCatalog(JSON.parse(JSON.stringify(catalog))).categories.find(c=>c.id==='kits').previewKey,kits.previewKey);
 kits.previewKey='';assert.ok(validateCatalog(catalog).some(e=>e.includes('unlisted preview link')));
 kits.previewKey=key;catalog.categories[0].previewKey=key;assert.ok(validateCatalog(catalog).some(e=>e.includes('unique valid keys')));
});
