import {designKey} from './keycaps.js';
// Public merchandise data contains retail prices and customer shipping, never credentials.
export const money = (value) => Math.round(Number(value) * 100) / 100;
export const merchVariants = (product) => (product?.merch?.variants || []).filter(v => v.enabled);
export const variantLabel = (variant) => [variant?.color, variant?.size].filter(Boolean).join(' / ');
export const cartLineKey = (id, variantId = '', design = null) => JSON.stringify([id, variantId || '', ...(design ? [designKey(design)] : [])]);
export function priceLabel(product) {
  if (product.pricePending) return 'Pricing to be announced';
  const prices = merchVariants(product).map(v => v.price);
  const low = prices.length ? Math.min(...prices) : product.price;
  const high = prices.length ? Math.max(...prices) : low;
  if (low === 0 && high === 0) return 'FREE';
  return `$${Number(low).toFixed(2)}${high > low ? `–$${high.toFixed(2)}` : ''}`;
}
const sizeOrder = ['XS','S','M','L','XL','2XL','3XL','4XL','5XL','6XL'];
export function compareSizes(a,b) {
  const ai=sizeOrder.indexOf(a), bi=sizeOrder.indexOf(b);
  if (ai >= 0 || bi >= 0) return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
  return a.localeCompare(b, undefined, {numeric:true});
}
export const sortSizes = values => [...values].sort(compareSizes);
export function optionValues(product, field, selectedColor = '') {
  return [...new Set(merchVariants(product).filter(v => field !== 'size' || !selectedColor || v.color === selectedColor).map(v => v[field]).filter(Boolean))].sort(field === 'size' ? compareSizes : (a,b) => a.localeCompare(b));
}
export function findVariant(product, color, size) {
  return merchVariants(product).find(v => (v.color || '') === color && (v.size || '') === size) || null;
}
export function importPrintifyProduct(product, detail, shopId, keepPrices = true) {
  const previous = new Map((product.merch?.productId === detail.id ? product.merch.variants : []).map(v => [v.id, v]));
  const variants = detail.variants.filter(v => v.enabled).map(v => {
    const old = previous.get(String(v.id));
    const image = detail.images?.find(i => i.variantIds.includes(v.id))?.src || '';
    return {id: String(v.id), providerVariantId: v.id, sku: v.sku || '', size: v.size || '', color: v.color || '',
      colors: v.colors || [], price: keepPrices && old ? old.price : v.priceCents / 100,
      enabled: old ? old.enabled : true, available: v.available, image};
  });
  return {...product, trackStock: false, pricePending: !variants.length,
    price: variants.length ? Math.min(...variants.filter(v => v.enabled).map(v => v.price).concat(variants.every(v => !v.enabled) ? [product.price] : [])) : product.price,
    merch: {provider: 'printify', productId: detail.id, shopId, blueprintId: detail.blueprintId,
      printProviderId: detail.printProviderId, syncedAt: new Date().toISOString(),
      shippingCountries: product.merch?.shippingCountries || ['US','CA'],
      shippingProfiles: detail.shippingProfiles || [], shippingWarning: detail.shippingWarning || '', variants}};
}
// Standard provider rates are an estimate, not an address-specific checkout quote.
export function shippingFor(product, variant, country) {
  if (!variant || !product.merch?.shippingCountries?.includes(country)) return null;
  const profiles = (product.merch.shippingProfiles || []).filter(p => p.variantIds.includes(variant.providerVariantId));
  return profiles.find(p => p.countries.includes(country)) || profiles.find(p => p.countries.includes('REST_OF_THE_WORLD')) || null;
}
export function estimateShipping(items, country) {
  const groups = new Map();
  for (const item of items.filter(i => i.product.type !== 'digital')) {
    const rate = shippingFor(item.product, item.variant, country);
    if (!rate) return null;
    // Separate products conservatively: different products/providers can ship separately.
    const key = JSON.stringify([item.product.id, rate]);
    const group = groups.get(key) || {rate, qty:0};
    group.qty += item.qty; groups.set(key, group);
  }
  return money([...groups.values()].reduce((sum, {rate,qty}) => sum + rate.firstItem + rate.additionalItem * (qty-1), 0));
}
export function hydrateLine(entry, product) {
  const variant = product.merch ? product.merch.variants.find(v => v.id === entry.variantId) || null : null;
  return {...entry, product, variant, key: cartLineKey(entry.id, entry.variantId, entry.design), price: variant?.price ?? product.price};
}
