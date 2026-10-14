import test from 'node:test';
import assert from 'node:assert/strict';
import { shippingCountries, setShippingCountry, shippingLabel } from './shipping-destinations.js';

test('country controls preserve legacy coverage and shipping rates across product types', () => {
  for (const product of [
    {type:'physical',keycaps:{profileId:'test'},officeShipping:{US:{firstItem:15},CA:{firstItem:25}}},
    {type:'physical',supplier:{provider:'mouser'},officeShipping:{CA:{firstItem:25}}},
    {type:'physical',supplier:{provider:'aliexpress'},shippingCountries:['US']},
    {type:'physical',merch:{shippingCountries:['US','CA'],shippingProfiles:[{countries:['US','CA'],firstItem:8}]}}
  ]) {
    const rates=JSON.stringify(product.officeShipping),profiles=JSON.stringify(product.merch?.shippingProfiles);
    setShippingCountry(product,'US',false);setShippingCountry(product,'CA',true);
    assert.deepEqual(shippingCountries(product),['CA']);
    assert.equal(shippingLabel(product),'Ships to Canada only');
    if(product.merch) assert.deepEqual(product.merch.shippingCountries,['CA']);
    setShippingCountry(product,'US',true);
    assert.deepEqual(shippingCountries(product),['US','CA']);
    assert.equal(JSON.stringify(product.officeShipping),rates);
    assert.equal(JSON.stringify(product.merch?.shippingProfiles),profiles);
    setShippingCountry(product,'CA',false);setShippingCountry(product,'US',false);
    assert.deepEqual(shippingCountries(product),[]);
    assert.equal(shippingLabel(product),'Shipping unavailable');
  }
  assert.equal(shippingLabel({type:'digital'}),'');
});
