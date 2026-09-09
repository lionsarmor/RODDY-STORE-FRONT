import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  normalizeCatalog,
  normalizeProduct,
  validateCatalog,
  safeLink,
} from "./catalog-model.js";
const data = JSON.parse(
  readFileSync(new URL("../public/data/products.json", import.meta.url)),
);
test("published catalog is valid without requiring obsolete starter content", () => {
  const c = normalizeCatalog(data);
  assert.deepEqual(validateCatalog(c), []);
  // Admin owns names, prices, availability and product count. Editing those
  // should not break the build's tests against an old six-product seed.
  assert.equal(c.products.length, data.products.length);
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
