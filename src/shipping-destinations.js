export const SHIPPING_COUNTRIES = { US: 'United States', CA: 'Canada' };

// Preserve legacy rates and imported provider coverage until an owner makes a choice.
export function shippingCountries(product) {
  if (product.type !== 'physical') return [];
  const allowed = product.shippingCountries ?? product.merch?.shippingCountries ??
    (Object.keys(product.officeShipping || {}).length ? Object.keys(product.officeShipping) : ['US', 'CA']);
  return Array.isArray(allowed) ? Object.keys(SHIPPING_COUNTRIES).filter(c => allowed.includes(c)) : [];
}

export function setShippingCountry(product, country, enabled) {
  if (!Object.hasOwn(SHIPPING_COUNTRIES, country)) return;
  const selected = new Set(shippingCountries(product));
  if (enabled) selected.add(country); else selected.delete(country);
  product.shippingCountries = Object.keys(SHIPPING_COUNTRIES).filter(c => selected.has(c));
  if (product.merch) product.merch.shippingCountries = [...product.shippingCountries];
}

export function shippingLabel(product) {
  if (product.type !== 'physical') return '';
  const countries = shippingCountries(product);
  return countries.length ? `Ships to ${countries.map(c => SHIPPING_COUNTRIES[c]).join(' & ')}${countries.length === 1 ? ' only' : ''}` : 'Shipping unavailable';
}
