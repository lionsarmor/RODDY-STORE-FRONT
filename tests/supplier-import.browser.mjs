// Run against a local Vite server. All GitHub/provider writes and reads are mocked;
// this test never publishes products, authenticates a buyer, or places an order.
// PLAYWRIGHT_MODULE may point to an existing Playwright installation.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const {chromium} = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.SUPPLIER_TEST_BASE_URL || 'http://127.0.0.1:5180';
const api = 'https://supplier-import.test';
const catalog = JSON.parse(readFileSync(new URL('../public/data/products.json', import.meta.url)));
catalog.settings.checkoutEndpoint = api;
const listing = (sku, name) => ({provider: 'aliexpress', sku, name, image: '', url: `https://www.aliexpress.com/item/${sku}.html`, variants: [], costCents: 2000, currency: 'USD', minimumQuantity: 1, orderMultiple: 1});
const rows = [listing('1005009999001', 'Hub with options'), listing('1005009999002', 'Single option hub'), listing('1005009999003', 'Missing SKU hub'), listing('1005009999004', 'Retry hub')];
const options = [{id: 'black', label: 'Black', costCents: 2000, availableQuantity: 4}, {id: 'silver', label: 'Silver', costCents: 2200, availableQuantity: 3}];
const calls = new Map();
const favorites = [{id: 'retro', provider: 'aliexpress', name: 'Retro Castle', storeId: '912024455', url: 'https://www.aliexpress.com/store/912024455', query: 'MiSTer FPGA'}];
const browser = await chromium.launch({headless: true});
try {
  const context = await browser.newContext({viewport: {width: 1280, height: 1000}});
  await context.addInitScript(() => localStorage.setItem('roddy:admin:config', JSON.stringify({owner: 'lionsarmor', repo: 'RODDY-STORE-FRONT', branch: 'main', token: 'fixture-owner', remember: true})));
  await context.route('**/*', route => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin === new URL(base).origin) return route.continue();
    if (url.origin === 'https://api.github.com' && request.method() === 'GET') return route.fulfill({json: url.pathname.includes('/git/trees/') ? {tree: []} : {sha: 'a'.repeat(40), content: Buffer.from(JSON.stringify(catalog)).toString('base64')}});
    if (url.origin !== api) return route.abort();
    if (url.pathname === '/admin/suppliers' && request.method() === 'GET') return route.fulfill({json: {connections: [{provider: 'aliexpress', searchConfigured: true, buyerAuthorized: true}], preferences: {favorites, revision: 1}}});
    if (url.pathname.endsWith('/search')) return route.fulfill({json: {products: rows, total: rows.length, hasMore: false, checkedAt: 1}});
    if (url.pathname.endsWith('/product')) {
      const sku = request.postDataJSON().query, count = (calls.get(sku) || 0) + 1;
      calls.set(sku, count);
      if (sku === rows[3].sku && count === 1) return route.fulfill({status: 503, json: {error: 'Supplier lookup temporarily unavailable. Retry this item.'}});
      const variants = sku === rows[1].sku ? options.slice(0, 1) : sku === rows[2].sku ? [] : options;
      return route.fulfill({json: {product: {...rows.find(row => row.sku === sku), sellerId: '2222222', sellerName: 'Another seller', variants}, checkedAt: 2}});
    }
    return route.abort();
  });
  const page = await context.newPage(), errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(base + '/admin.html');
  await page.getByRole('button', {name: /Connect to publish/}).click();
  await page.getByRole('button', {name: 'Connect & load catalog', exact: true}).click();
  await page.getByRole('status').filter({hasText: 'Connected.'}).waitFor();
  const suppliers = () => page.getByRole('button', {name: /Suppliers & imports/}).click();
  await suppliers();
  const search = async () => {
    await page.getByLabel('Keywords, part number, or product URL', {exact: true}).fill('USB hub');
    await page.getByRole('button', {name: 'Search supplier API', exact: true}).click();
    await page.getByRole('heading', {name: rows[0].name, exact: true}).waitFor();
  };
  const card = name => page.locator('.supplier-block').filter({has: page.getByRole('heading', {name, exact: true})});
  const multi = card(rows[0].name), sole = card(rows[1].name), missing = card(rows[2].name), retry = card(rows[3].name);
  const checkbox = row => row.getByLabel('Select for import', {exact: true});
  const variant = row => row.getByLabel('Exact supplier variant', {exact: true});
  const review = page.locator('.supplier-review');
  const addSelected = review.getByRole('button', {name: 'Add selected as hidden product drafts', exact: true});
  await page.getByLabel('Department for new items', {exact: true}).selectOption('computers');
  await search();
  assert.equal(calls.size, 0);
  assert.ok(await checkbox(multi).isEnabled());
  await checkbox(multi).check();
  await variant(multi).waitFor();
  assert.equal(calls.get(rows[0].sku), 1);
  assert.ok(await checkbox(multi).isChecked());
  await page.getByRole('button', {name: 'Review selection (1)', exact: true}).click();
  assert.ok(await addSelected.isDisabled());
  await variant(review).selectOption('silver');
  assert.ok(await checkbox(multi).isChecked());
  assert.ok(await addSelected.isEnabled());
  await checkbox(multi).uncheck();
  assert.ok(await page.getByRole('button', {name: 'Review selection (0)', exact: true}).isDisabled());

  // Direct add loads details, reports the failure inline, and offers a retry.
  await retry.getByRole('button', {name: 'Choose options & add', exact: true}).click();
  await retry.getByRole('alert').filter({hasText: 'temporarily unavailable'}).waitFor();
  assert.ok(await checkbox(retry).isEnabled());
  await retry.getByRole('button', {name: 'Choose options & add', exact: true}).click();
  await variant(retry).waitFor();
  assert.ok(await variant(retry).evaluate(element => element === document.activeElement));
  assert.equal(await variant(retry).inputValue(), '');
  assert.equal(calls.get(rows[3].sku), 2);
  await variant(retry).selectOption('black');
  await retry.getByRole('button', {name: 'Add & edit product', exact: true}).click();
  await page.locator('.editor-panel').waitFor();
  assert.equal(await page.locator('.editor-panel').getByLabel(/^Department/).inputValue(), 'computers');
  await page.getByLabel('Product name', {exact: true}).fill('Owner edited hub');
  await page.getByLabel('Full description', {exact: true}).fill('Owner description stays intact.');
  await page.getByRole('tab', {name: 'supplier', exact: true}).click();
  assert.equal(await page.getByLabel(/^Fulfillment mode/).inputValue(), 'pending');
  await suppliers();
  assert.ok(await checkbox(retry).isDisabled());
  await retry.getByRole('button', {name: 'Already in RODDY — edit', exact: true}).click();
  await page.getByRole('tab', {name: 'details', exact: true}).click();
  assert.equal(await page.getByLabel('Product name', {exact: true}).inputValue(), 'Owner edited hub');
  assert.equal(await page.getByLabel('Full description', {exact: true}).inputValue(), 'Owner description stays intact.');
  await suppliers();
  await variant(retry).selectOption('silver');
  assert.ok(await checkbox(retry).isEnabled());

  // A sole exact option needs no extra choice; missing SKU data stays blocked.
  await checkbox(sole).check();
  await variant(sole).waitFor();
  assert.equal(await variant(sole).inputValue(), 'black');
  await checkbox(missing).check();
  await missing.getByText('The supplier returned no exact options.', {exact: false}).waitFor();
  assert.ok(await checkbox(missing).isChecked());
  await page.getByRole('button', {name: 'Review selection (2)', exact: true}).click();
  assert.ok(await addSelected.isDisabled());
  const missingReview = review.locator('tr').filter({hasText: rows[2].name});
  await missingReview.getByRole('button', {name: 'Retry loading options', exact: true}).click();
  assert.equal(calls.get(rows[2].sku), 2);
  await missingReview.getByRole('button', {name: 'Remove from selection', exact: true}).click();
  assert.ok(await addSelected.isEnabled());
  await addSelected.click();
  await page.getByRole('status').filter({hasText: '1 hidden draft(s) added'}).waitFor();

  // Bulk page selection works before details; it does not fire a quota burst.
  await search();
  const beforeBulk = [...calls.values()].reduce((a, b) => a + b, 0);
  await page.getByRole('button', {name: 'Select results on this page', exact: true}).click();
  assert.ok(await checkbox(multi).isChecked());
  assert.ok(await checkbox(missing).isChecked());
  assert.equal([...calls.values()].reduce((a, b) => a + b, 0), beforeBulk);
  await page.getByRole('button', {name: /Review selection \(/}).click();
  assert.ok(await addSelected.isDisabled());
  await review.locator('tr').filter({hasText: rows[0].name}).getByRole('button', {name: 'Load options', exact: true}).click();
  assert.ok(await checkbox(multi).isChecked());
  await page.getByRole('button', {name: 'Clear selection', exact: true}).click();

  // An explicitly chosen seller restriction still prevents incorrect imports.
  await page.getByLabel('Seller filter', {exact: true}).selectOption('retro');
  await search();
  await checkbox(multi).check();
  await variant(multi).waitFor();
  await variant(multi).selectOption('black');
  assert.ok(await multi.getByRole('button', {name: 'Add & edit product', exact: true}).isDisabled());
  await page.getByRole('button', {name: 'Search all suppliers', exact: true}).click();
  assert.ok(await multi.getByRole('button', {name: 'Add & edit product', exact: true}).isEnabled());
  await page.setViewportSize({width: 390, height: 844});
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  assert.deepEqual(errors, []);
  console.log('PASS: immediate selection, automatic options, retained checks, review choices, direct add, retry, exact-SKU guard, sole option, bulk quota protection, duplicate/editor preservation, seller filter and mobile fit. All external operations mocked.');
} finally { await browser.close(); }
