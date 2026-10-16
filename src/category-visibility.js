// Unlisted merchandising, not authentication: catalog data and downloads remain
// public assets. A link enables browsing one hidden category in this tab's URL.
export const CATEGORY_PREVIEW_PARAM = 'category-preview';
export const validPreviewKey = key => typeof key === 'string' && /^[a-zA-Z0-9_-]{16,80}$/.test(key);

export function categoryVisible(category, previewKey = '', draftPreview = false) {
  return category?.visible !== false || draftPreview ||
    (validPreviewKey(category.previewKey) && category.previewKey === previewKey);
}

export function visibleProducts(products, categories, previewKey = '', draftPreview = false) {
  return products.filter(product => product.active && categoryVisible(
    categories.find(category => category.id === product.category), previewKey, draftPreview,
  ));
}

export function categoryPreviewUrl(base, category) {
  const url = new URL('./', base);
  if (category.visible === false && validPreviewKey(category.previewKey))
    url.searchParams.set(CATEGORY_PREVIEW_PARAM, category.previewKey);
  url.hash = '/shop?' + new URLSearchParams({ cat: category.id });
  return url.href;
}
