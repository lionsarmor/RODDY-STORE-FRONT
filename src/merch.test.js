import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeCatalog, validateCatalog } from './catalog-model.js';
import { importPrintifyProduct, optionValues, findVariant, priceLabel, shippingFor, estimateShipping, hydrateLine, cartLineKey, sortSizes } from './merch.js';
const product = {id:'hoodie', name:'Hoodie', price:35.99, type:'physical', merch:{productId:'abc', shippingCountries:['US','CA'], variants:[
  {id:'1',providerVariantId:1,color:'Black',size:'S',price:35.99,enabled:true,available:true},
  {id:'2',providerVariantId:2,color:'Black',size:'5XL',price:42.99,enabled:true,available:true},
  {id:'3',providerVariantId:3,color:'Orchid',size:'S',price:35.99,enabled:true,available:false},
  {id:'4',providerVariantId:4,color:'White',size:'S',price:35.99,enabled:false,available:true}],
  shippingProfiles:[{countries:['US'],variantIds:[1,2,3,4],firstItem:8.79,additionalItem:2.09},{countries:['CA'],variantIds:[1,2,3,4],firstItem:13.19,additionalItem:6.59}]}};
test('option selection excludes disabled variants and never invents missing color/size combinations',()=>{
  assert.deepEqual(optionValues(product,'color'),['Black','Orchid']);
  assert.deepEqual(optionValues(product,'size','Orchid'),['S']);
  assert.equal(findVariant(product,'Orchid','5XL'),null);
  assert.equal(findVariant(product,'Orchid','S').available,false);
  assert.equal(priceLabel(product),'$35.99–$42.99');
  assert.deepEqual(sortSizes(['XL','5XL','S','M','4XL','L','3XL','2XL']),['S','M','L','XL','2XL','3XL','4XL','5XL']);
});
test('cart lines retain each color/size and always hydrate the current retail price',()=>{
  const small=hydrateLine({id:'hoodie',variantId:'1',qty:1},product);
  const large=hydrateLine({id:'hoodie',variantId:'2',qty:2},product);
  assert.notEqual(small.key,large.key);
  assert.equal(small.price,35.99);assert.equal(large.price,42.99);
  assert.equal(hydrateLine({id:'hoodie',variantId:'deleted'},product).variant,null);
  assert.equal(cartLineKey('a:b','c'),cartLineKey('a:b','c'));
  assert.notEqual(cartLineKey('a:b','c'),cartLineKey('a','b:c'));
});
test('shipping uses country and variant, charges first/additional correctly and never treats missing rates as free',()=>{
  const items=[hydrateLine({id:'hoodie',variantId:'1',qty:1},product),hydrateLine({id:'hoodie',variantId:'2',qty:2},product)];
  assert.equal(estimateShipping(items,'US'),12.97);
  assert.equal(estimateShipping(items,'CA'),26.37);
  assert.equal(estimateShipping(items,'GB'),null);
  assert.equal(shippingFor(product,null,'US'),null);
  const mat={id:'mat',type:'physical',merch:{...product.merch,shippingProfiles:[{countries:['US'],variantIds:[1],firstItem:10.79,additionalItem:7.20}]}};
  assert.equal(estimateShipping([...items,hydrateLine({id:'mat',variantId:'1',qty:1},mat)],'US'),23.76);
  assert.equal(estimateShipping([],'US'),0);
});
test('Printify sync keeps edited retail prices and offer flags, replaces stock and drops supplier-disabled variants',()=>{
  const previous=structuredClone(product);previous.merch.variants[0].enabled=false;
  const detail={id:'abc',blueprintId:77,printProviderId:99,images:[],shippingProfiles:[],variants:[
    {id:1,color:'Black',size:'S',enabled:true,available:false,priceCents:3596,costCents:2158},
    {id:2,color:'Black',size:'5XL',enabled:false,available:true,priceCents:4276},
    {id:5,color:'Navy',size:'S',enabled:true,available:true,priceCents:3596}]};
  const result=importPrintifyProduct(previous,detail,123);
  assert.equal(result.merch.variants.length,2);
  assert.equal(result.merch.variants[0].price,35.99);assert.equal(result.merch.variants[0].enabled,false);
  assert.equal(result.merch.variants[0].available,false);assert.equal(result.merch.variants[1].price,35.96);
  assert.ok(!JSON.stringify(result).includes('costCents'));
  assert.equal(result.price,35.96);
});
test('catalog validation rejects unmapped variants, duplicate combinations and invalid retail prices',()=>{
  const p={...structuredClone(product),sku:'R-TEST',category:'merch',status:'available',stock:0,active:true,tags:[]};
  Object.assign(p.merch,{provider:'printify',shopId:123});
  const catalog=normalizeCatalog({products:[p],categories:[{id:'merch',name:'Merch'}],settings:{heroProductId:''}});
  assert.deepEqual(validateCatalog(catalog),[]);
  catalog.products[0].merch.variants[0].price=-1;
  catalog.products[0].merch.variants[1].providerVariantId=null;
  const errors=validateCatalog(catalog).join(' ');
  assert.match(errors,/valid retail price/);assert.match(errors,/mapped to Printify/);
});
