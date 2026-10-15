import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { productOrigin } from './product-origin.js';
import {
  normalizeCatalog,
  normalizeProduct,
  validateCatalog,
  safeLink,
  customerLink,
  pdfDocumentation,
} from "./catalog-model.js";
const data = JSON.parse(
  readFileSync(new URL("../public/data/products.json", import.meta.url)),
);
test('design credit requires explicit authorship and survives catalog editing', () => {
  for (const product of [{}, { type: 'physical', status: 'available' }, { category: 'labs', status: 'coming-soon' }, { type: 'digital' }]) {
    assert.equal(normalizeProduct(product).designOrigin, 'selected');
    assert.equal(productOrigin(product).label, 'RODDY SELECT');
  }
  const c = normalizeCatalog(structuredClone(data));
  const p = c.products[0];
  p.designOrigin = 'original';
  assert.equal(productOrigin(normalizeCatalog(JSON.parse(JSON.stringify(c))).products[0]).label, 'RODDY ORIGINAL');
  p.designOrigin = 'invalid';
  assert.equal(productOrigin(p).label, 'RODDY SELECT');
  assert.ok(validateCatalog(c).some(e => e.includes('design credit')));
});
test("published catalog is valid without requiring obsolete starter content", () => {
  const c = normalizeCatalog(data);
  assert.deepEqual(validateCatalog(c), []);
  // Admin owns names, prices, availability and product count. Editing those
  // should not break the build's tests against an old six-product seed.
  assert.equal(c.products.length, data.products.length);
});
test('customer links exclude GitHub hosts and Labs documentation uses PDFs', () => {
  for (const url of ['https://github.com/owner/repo', 'https://api.github.com/repos/owner/repo', 'https://raw.githubusercontent.com/owner/repo/main/file.pdf', 'https://owner.github.io/manual.pdf']) {
    assert.equal(customerLink(url), '');
  }
  assert.equal(pdfDocumentation('https://roddy.world/downloads/manual.pdf'), 'https://roddy.world/downloads/manual.pdf');
  assert.equal(pdfDocumentation('https://roddy.world/manual'), '');
  const catalog = normalizeCatalog(structuredClone(data));
  const lab = catalog.products.find(p => p.category === 'labs');
  lab.documentationUrl = 'https://roddy.world/manual';
  assert.ok(validateCatalog(catalog).some(e => e.includes('Labs documentation')));
  for (const p of data.products) {
    assert.equal(p.githubUrl || '', '');
    if(p.downloadUrl) assert.ok(customerLink(p.downloadUrl));
    if(p.category === 'labs' && p.active) assert.ok(pdfDocumentation(p.documentationUrl));
  }
});
test('available products need final pricing and supported shipping destinations',()=>{
  const c=normalizeCatalog(structuredClone(data)),p=c.products.find(p=>p.active && p.status==='available');
  p.pricePending=true;assert.ok(validateCatalog(c).some(e=>e.includes('final price')));
  p.status='coming-soon';assert.ok(!validateCatalog(c).some(e=>e.includes('final price')));
  p.pricePending=false;p.status='available';p.fulfillment='pending';assert.ok(validateCatalog(c).some(e=>e.includes('ready fulfillment')));
  p.fulfillment='manual';assert.ok(!validateCatalog(c).some(e=>e.includes('ready fulfillment')));
  p.shippingCountries=['US','CA'];assert.ok(!validateCatalog(c).some(e=>e.includes('shipping destinations')));
  for(const countries of [[],['GB'],['US','US'],'US']){
    p.shippingCountries=countries;assert.ok(validateCatalog(c).some(e=>e.includes('shipping destinations')));
  }
});
test("legacy images migrate and explicit cover stays separate from the gallery", () => {
  assert.deepEqual(normalizeProduct({ image: "old.jpg" }).images, ["old.jpg"]);
  const p = normalizeProduct({
    coverImage: "cover.jpg",
    images: ["one.jpg", "two.jpg"],
  });
  assert.equal(p.coverImage, "cover.jpg");
  assert.deepEqual(p.images, ["one.jpg", "two.jpg"]);
});
test("validation rejects misleading free labels, contradictory AI labels and bad links", () => {
  const c = normalizeCatalog(structuredClone(data));
  Object.assign(c.products[0], {
    price: 20,
    tags: ["free", "ai-assisted", "no-ai"],
    downloadUrl: "javascript:alert(1)",
  });
  const errors = validateCatalog(c).join(" ");
  assert.match(errors, /FREE requires/);
  assert.match(errors, /choose AI Assisted/);
  assert.match(errors, /HTTP\(S\)/);
});
test("link protocol allowlist excludes script URLs", () => {
  assert.equal(safeLink("javascript:alert(1)"), "");
  assert.equal(safeLink("data:text/html,hello"), "");
  assert.equal(
    safeLink("https://github.com/roddy/app"),
    "https://github.com/roddy/app",
  );
});

test("paid products cannot publish a free-download URL", () => {
  const c = normalizeCatalog(structuredClone(data));
  c.products[0].price = 3.99;
  c.products[0].downloadUrl = "https://example.com/private.zip";
  assert.ok(validateCatalog(c).some((e) => e.includes("public free-download")));
});

test("product editorial fields are optional and survive catalog round trips", () => {
  const legacy = normalizeProduct({ id: "legacy" });
  assert.equal(legacy.story, "");
  assert.equal(legacy.documentationUrl, "");
  const product = {
    ...data.products[0],
    story: "A machine worth understanding.",
    documentationUrl: "https://example.com/manual",
  };
  const catalog = normalizeCatalog({ ...data, products: [product] });
  const restored = normalizeCatalog(JSON.parse(JSON.stringify(catalog)))
    .products[0];
  assert.equal(restored.story, product.story);
  assert.equal(restored.documentationUrl, product.documentationUrl);
});

test("documentation links reject executable and non-web URLs", () => {
  const catalog = normalizeCatalog(structuredClone(data));
  for (const url of [
    "javascript:alert(1)",
    "data:text/html,test",
    "file:///etc/passwd",
    "https://example.com/docs",
    "",
  ]) {
    catalog.products[0].documentationUrl = url;
    const errors = validateCatalog(catalog).filter((error) =>
      error.includes("documentation"),
    );
    assert.equal(
      errors.length,
      url === "" || url.startsWith("https://") ? 0 : 1,
    );
  }
});
