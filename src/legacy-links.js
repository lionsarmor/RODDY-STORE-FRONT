// Upgrade old storefront bookmarks without touching order receipts or admin.
export function legacyStoreTarget(value) {
  const url = new URL(value);
  if (!['/', '/index.html'].includes(url.pathname)) return null;
  if (!url.hash.startsWith('#/')) return url.pathname === '/index.html' ? '/' + url.search : null;
  const route = url.hash.slice(1);
  // A hash route must stay on this origin, including malformed old links.
  if (route.startsWith('//') || route.includes('\\') || /[\x00-\x1f]/.test(route)) return null;
  const target = new URL(route, url.origin);
  for (const [key, value] of url.searchParams) if (!target.searchParams.has(key)) target.searchParams.append(key, value);
  return target.pathname + target.search + target.hash;
}
