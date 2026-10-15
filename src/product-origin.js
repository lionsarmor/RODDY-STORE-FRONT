export const PRODUCT_ORIGINS = [
  { id: 'original', label: 'RODDY ORIGINAL', description: 'Designed and developed by RODDY.' },
  { id: 'design', label: 'RODDY DESIGN', description: 'RODDY artwork or customization on an existing product.' },
  { id: 'selected', label: 'RODDY SELECT', description: 'From another maker, selected for the RODDY store.' },
  { id: 'community', label: 'COMMUNITY DESIGN', description: 'Based on a community hardware or software design.' },
];

// Authorship is explicit, never inferred from stock, category or fulfillment.
export function productOrigin(product) {
  return PRODUCT_ORIGINS.find(origin => origin.id === product.designOrigin)
    || PRODUCT_ORIGINS.find(origin => origin.id === 'selected');
}
