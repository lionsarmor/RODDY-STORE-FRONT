// Read-only production smoke check. Never creates orders, subscribers or emails.
import assert from 'node:assert/strict';

const site = 'https://roddy.world';
const request = (url, options = {}) => fetch(url, {...options, signal: AbortSignal.timeout(20000)});
for (const host of ['roddy.world', 'www.roddy.world']) {
  for (const path of ['/', '/product/buddy/', '/product/orbit/', '/admin.html', '/order.html']) {
    const url = new URL('http://' + host + path);
    url.searchParams.set('connection-check', Date.now());
    const response = await request(url, {redirect: 'manual'});
    assert.ok([301, 302, 307, 308].includes(response.status), `HTTP must redirect: ${url}`);
    const target = new URL(response.headers.get('location'), url);
    assert.equal(target.protocol, 'https:', `First redirect must enable HTTPS: ${url}`);
    assert.equal(target.pathname, url.pathname);
    assert.equal(target.search, url.search);
  }
}
const catalogResponse = await request(site + '/data/products.json');
assert.equal(catalogResponse.status, 200);
const {settings} = await catalogResponse.json();
const api = settings.checkoutEndpoint.replace(/\/$/, '');
assert.equal(new URL(api).protocol, 'https:');
const health = await request(api + '/health');
assert.equal(health.status, 200);
assert.equal((await health.json()).configured, true);

for (const origin of [site, 'https://www.roddy.world']) {
  for (const path of ['/newsletter/subscribe', '/quote', '/checkout', '/free-downloads', '/order', '/customer/me', '/admin/orders', '/forum/topics']) {
    const response = await request(api + path, {method: 'OPTIONS', headers: {
      origin, 'access-control-request-method': 'POST',
      'access-control-request-headers': 'content-type,authorization',
    }});
    assert.equal(response.status, 200, `${origin} ${path}`);
    assert.equal(response.headers.get('access-control-allow-origin'), origin);
    assert.match(response.headers.get('access-control-allow-methods'), /POST/);
    assert.match(response.headers.get('access-control-allow-headers'), /authorization/i);
  }
  const inventory = await request(api + '/inventory', {headers: {origin}});
  assert.equal(inventory.status, 200);
  assert.equal(inventory.headers.get('access-control-allow-origin'), origin);
  const account = await request(api + '/customer/me', {headers: {origin}});
  assert.equal(account.status, 401); // Auth required, but response must reach the browser.
  assert.equal(account.headers.get('access-control-allow-origin'), origin);
}
console.log('PASS: HTTP links upgrade to HTTPS; store API, inventory and account responses are reachable; newsletter, shipping, checkout, free downloads, receipts, accounts, admin and community preflights accept both secure site origins.');
