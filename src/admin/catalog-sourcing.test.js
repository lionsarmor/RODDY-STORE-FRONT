import test from 'node:test';import assert from 'node:assert/strict';
import {publicCatalog,hydrateCatalog} from './catalog-sourcing.js';
import {shippingFor} from '../merch.js';
test('publishing strips supplier identities while admin restores private mappings and current retail prices',()=>{
 const catalog={products:[{id:'keyboard',supplier:{provider:'aliexpress',supplierSku:'secret-listing',variantId:'secret-sku',fulfillment:'manual'}},{id:'hoodie',merch:{provider:'printify',productId:'secret-product',shopId:123,shippingCountries:['US'],shippingProfiles:[{variantIds:[42],countries:['US'],firstItem:5,additionalItem:1}],variants:[{id:'42',providerVariantId:42,size:'M',color:'Black',price:49.99,enabled:true,available:true}]}}]};
 const references={keyboard:'k-ref',hoodie:'h-ref'},publicData=publicCatalog(catalog,references),text=JSON.stringify(publicData);
 for(const secret of ['aliexpress','printify','secret-listing','secret-sku','secret-product','providerVariantId','shopId'])assert.ok(!text.includes(secret));
 assert.equal(publicData.products[0].fulfillment,'manual');assert.equal(shippingFor(publicData.products[1],publicData.products[1].merch.variants[0],'US').firstItem,5);
 publicData.products[1].merch.variants[0].price=54.99;
 const sources={keyboard:{'k-ref':{supplier:catalog.products[0].supplier}},hoodie:{'h-ref':{merch:catalog.products[1].merch}}};
 const privateData=hydrateCatalog(publicData,sources);assert.equal(privateData.products[1].merch.productId,'secret-product');assert.equal(privateData.products[1].merch.variants[0].providerVariantId,42);assert.equal(privateData.products[1].merch.variants[0].price,54.99);assert.equal(catalog.products[1].merch.variants[0].price,49.99);
 assert.throws(()=>hydrateCatalog(publicData,{}),/private product mapping/);
});
