import { normalizeProduct } from '../catalog-model.js';
import { slugify } from './utils.js';

export function supplierIdentity(product) {
  const s = product.supplier || product;
  return JSON.stringify([s.provider, String(s.supplierSku || s.sku || '').toLowerCase(), s.variantId || '']);
}

function basisPoints(value, label) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0 || n > 500 || Math.abs(n * 100 - Math.round(n * 100)) > .000001) throw new Error(`Check ${label}; use a percentage with up to two decimals.`);
  return Math.round(n * 100);
}
function cents(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0 || n > 999999 || Math.abs(n * 100 - Math.round(n * 100)) > .000001) throw new Error('Use valid USD amounts with at most two decimals.');
  return Math.round(n * 100);
}

export function priceEstimate(cost, rules) {
  if (!Number.isInteger(cost) || cost < 0 || cost > 99999999) return null;
  const landed = cost + cents(rules.shippingBuffer);
  const fixed = cents(rules.feeFixed), minimum = cents(rules.minimumProfit);
  const fee = basisPoints(rules.feePercent, 'processing fees');
  const percent = basisPoints(rules.percent, rules.mode === 'margin' ? 'margin' : 'markup');
  if (fee >= 10000 || (rules.mode === 'margin' && fee + percent >= 10000)) throw new Error('The target margin plus processing percentage must be below 100%.');
  let retail = rules.mode === 'margin' ? Math.ceil((landed + fixed) * 10000 / (10000 - fee - percent)) : Math.ceil(landed * (10000 + percent) / 10000);
  retail = Math.max(retail, Math.ceil((landed + fixed + minimum) * 10000 / (10000 - fee)));
  if (rules.round99) retail = Math.ceil((retail - 99) / 100) * 100 + 99;
  if (retail > 99999999) throw new Error('The estimated price is too high.');
  const fees = Math.ceil(retail * fee / 10000) + fixed;
  return {retail: retail / 100, profit: (retail - fees - landed) / 100, landed: landed / 100};
}

export function supplierDraft(row, variantId, category, rules, existing) {
  const variant = row.variants?.length ? row.variants.find(v => v.id === variantId) : null;
  if (row.provider === 'aliexpress' && (!variant || !variant.id)) throw new Error(`${row.name}: load details and choose an exact AliExpress variant first.`);
  const supplier = {provider: row.provider, supplierSku: row.sku, variantId: variant?.id || '', productUrl: row.url || '',
    manufacturer: row.manufacturer || '', manufacturerPartNumber: row.manufacturerPartNumber || '',
    sellerId: row.sellerId || '', sellerName: row.sellerName || '', fulfillment: 'pending', checkedAt: row.checkedAt || null,
    minimumQuantity: row.minimumQuantity || 1, orderMultiple: row.orderMultiple || 1};
  if (existing.some(p => p.supplier && supplierIdentity(p) === supplierIdentity(supplier))) throw new Error(`${row.name}: already imported. Edit its existing product instead.`);
  const estimate = priceEstimate(variant ? variant.costCents : row.costCents, rules);
  const base = 'roddy-item-'+crypto.randomUUID().slice(0,8);
  let id = base, sku = 'RODDY-'+base.slice(-8).toUpperCase(), n = 1;
  while (existing.some(p => p.id === id)) id = `${base}-${n++}`;
  while (existing.some(p => p.sku?.toLowerCase() === sku.toLowerCase())) sku += '-new';
  return normalizeProduct({id, sku, name: row.name + (variant?.label ? ` — ${variant.label}` : ''), category,
    type: 'physical', status: 'coming-soon', active: false, featured: false, price: estimate?.retail || 0,
    pricePending: !estimate, stock: 0, trackStock: true, description: row.description || row.name,
    shortDescription: '', images: row.image ? [row.image] : [], coverImage: row.image || '', tags: [],
    specs: {...(row.manufacturer ? {Manufacturer: row.manufacturer} : {}), ...(row.manufacturerPartNumber ? {'Manufacturer part': row.manufacturerPartNumber} : {}),
      ...(variant?.label ? {Variant: variant.label} : {})}, supplier, officeShipping: {},
    releaseNote: 'Coming soon.'});
}
