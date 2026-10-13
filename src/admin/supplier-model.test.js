import test from 'node:test';
import assert from 'node:assert/strict';
import {priceEstimate, supplierDraft} from './supplier-model.js';
import {validateCatalog, normalizeCatalog} from '../catalog-model.js';

const rules = {mode: 'markup', percent: 30, minimumProfit: 5, shippingBuffer: 15, feePercent: 2.9, feeFixed: .3, round99: true};
const row = {provider: 'mouser', sku: '123-FPGA', name: 'FPGA Board', costCents: 12001, image: 'https://example.com/a.jpg', url: 'https://www.mouser.com/test', minimumQuantity: 1, orderMultiple: 1, checkedAt: 100};

test('supplier estimates include shipping allowance, processing fees and minimum profit without rounding down', () => {
  const e = priceEstimate(12001, rules);
  assert.equal(e.retail, 175.99);
  assert.ok(e.profit >= 5);
  const minimum = priceEstimate(1, {...rules, percent: 0, shippingBuffer: 0, round99: false});
  assert.ok(minimum.profit >= 5);
  const margin = priceEstimate(12001, {...rules, mode: 'margin', percent: 20});
  assert.ok(margin.profit / margin.retail >= .2);
  assert.throws(() => priceEstimate(100, {...rules, mode: 'margin', percent: 98}));
  assert.throws(() => priceEstimate(100, {...rules, feePercent: 100}));
  assert.equal(priceEstimate(null, rules), null);
});

test('selected supplier imports are hidden pending drafts, preserve provenance and never publish private cost', () => {
  const p = supplierDraft(row, '', 'computers', rules, []);
  assert.equal(p.active, false); assert.equal(p.status, 'coming-soon'); assert.equal(p.stock, 0);
  assert.equal(p.supplier.fulfillment, 'pending'); assert.equal(p.price, 175.99);
  assert.ok(!JSON.stringify(p).includes('costCents'));
  assert.throws(() => supplierDraft(row, '', 'computers', rules, [p]), /already imported/);
  const catalog = normalizeCatalog({products: [p], categories: [{id: 'computers', name: 'Computers'}], settings: {heroProductId: ''}});
  assert.deepEqual(validateCatalog(catalog), []);
  p.supplier.fulfillment = 'automatic'; assert.ok(validateCatalog(catalog).some(e => e.includes('pending or office')));
});

test('AliExpress requires an exact variant; different SKUs import separately and unknown prices stay pending', () => {
  const ali = {...row, provider: 'aliexpress', sku: '1005001234567', variants: [{id: 'black', label: 'Black', costCents: 2995}, {id: 'red', label: 'Red', costCents: null}], sellerId: '1234567'};
  assert.throws(() => supplierDraft(ali, '', 'computers', rules, []), /exact AliExpress variant/);
  const black = supplierDraft(ali, 'black', 'computers', rules, []);
  assert.equal(black.supplier.variantId, 'black'); assert.equal(black.supplier.sellerId, '1234567');
  const red = supplierDraft({...ali, costCents: null}, 'red', 'computers', rules, [black]);
  assert.notEqual(black.id, red.id); assert.equal(red.pricePending, true); assert.equal(red.price, 0);
});
