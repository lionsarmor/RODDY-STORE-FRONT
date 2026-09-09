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
test("curated catalog is valid and contains the requested products and merch", () => {
  const c = normalizeCatalog(data);
  assert.deepEqual(validateCatalog(c), []);
  assert.equal(c.products.length, 6);
  assert.equal(
    c.products.find((p) => p.name === "DESK COMMANDER").category,
    "apps",
  );
  assert.equal(
    c.products.find((p) => p.name === "I KNOW WHAT I SAW").category,
    "games",
  );
  for (const id of ["keychain-kreatures", "kestrel-computer"])
    assert.equal(c.products.find((p) => p.id === id).status, "coming-soon");
  for (const name of ["DESK MAT", "HOODIE"]) {
    const product = c.products.find((p) => p.name === name);
    assert.equal(product.category, "merch");
    assert.equal(product.active, true);
    assert.equal(product.pricePending, true);
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
