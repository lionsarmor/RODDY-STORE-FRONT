import { ADMIN_ORIGIN, PRIVATE_ADMIN, STOREFRONT_ORIGIN } from './config';

const KEY = 'roddy:preview';
const REQUEST = 'roddy:draft-preview-request';
const DRAFT = 'roddy:draft-preview';
const TIMEOUT = 10_000;

export function openDraftPreview(draft) {
  if (!PRIVATE_ADMIN) {
    sessionStorage.setItem(KEY, draft);
    window.open('./index.html?preview=1#/', '_blank');
    return;
  }
  const preview = window.open(STOREFRONT_ORIGIN + '/?preview=1', '_blank');
  if (!preview) throw new Error('Preview popup is blocked.');
  function receive(event) {
    if (event.source !== preview || event.origin !== STOREFRONT_ORIGIN || event.data !== REQUEST) return;
    preview.postMessage({type: DRAFT, draft}, STOREFRONT_ORIGIN);
    clearTimeout(expiry);
    window.removeEventListener('message', receive);
  }
  const expiry = setTimeout(() => window.removeEventListener('message', receive), TIMEOUT);
  window.addEventListener('message', receive);
}

export async function readDraftPreview() {
  const cached = sessionStorage.getItem(KEY);
  if (!window.opener || location.origin !== STOREFRONT_ORIGIN) return cached;
  // Request from a fresh preview tab even if it inherited a prior draft.
  return new Promise(resolve => {
    function finish(value) {
      clearTimeout(expiry);
      window.removeEventListener('message', receive);
      resolve(value);
    }
    function receive(event) {
      if (event.source !== window.opener || event.origin !== ADMIN_ORIGIN ||
          event.data?.type !== DRAFT || typeof event.data.draft !== 'string') return;
      try { sessionStorage.setItem(KEY, event.data.draft); } catch { /* Preview still works for this page load. */ }
      window.opener = null;
      finish(event.data.draft);
    }
    const expiry = setTimeout(() => finish(cached), TIMEOUT);
    window.addEventListener('message', receive);
    window.opener.postMessage(REQUEST, ADMIN_ORIGIN);
  });
}
