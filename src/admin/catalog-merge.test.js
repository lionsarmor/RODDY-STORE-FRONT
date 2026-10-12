import test from "node:test";
import assert from "node:assert/strict";
import { mergeCatalog } from "./catalog-merge.js";

const catalog = () => ({ settings: { checkoutEnabled: false }, categories: [], tags: [], products: [
  { id: "desk", price: 3.99, description: "Original", images: ["old.jpg"], specs: { Platform: "X16" } },
  { id: "weather", price: 0, description: "Weather" },
] });

test("preserves newer checkout settings while applying a stale draft's product edits", () => {
  const base = catalog(), local = catalog(), remote = catalog();
  local.products[0].description = "My edit";
  remote.settings.checkoutEnabled = true;
  remote.products[0].images = ["new.jpg"];
  const result = mergeCatalog(base, local, remote);
  assert.deepEqual(result.conflicts, []);
  assert.equal(result.catalog.settings.checkoutEnabled, true);
  assert.equal(result.catalog.products[0].description, "My edit");
  assert.deepEqual(result.catalog.products[0].images, ["new.jpg"]);
  assert.deepEqual(base, catalog());
  result.catalog.products[0].description = "Another edit";
  assert.equal(local.products[0].description, "My edit");
});

test("combines separate nested fields and products regardless of array positions", () => {
  const base = catalog(), local = catalog(), remote = catalog();
  local.products[0].specs.Storage = "SD card";
  remote.products[0].specs.Platform = "Commander X16";
  remote.products.reverse();
  const result = mergeCatalog(base, local, remote);
  assert.deepEqual(result.conflicts, []);
  assert.equal(result.catalog.products[0].id, "weather");
  assert.deepEqual(result.catalog.products[1].specs, { Platform: "Commander X16", Storage: "SD card" });
});

test("same field changes require an explicit choice, without changing source drafts", () => {
  const base = catalog(), local = catalog(), remote = catalog();
  local.products[0].description = "Mine";
  remote.products[0].description = "Theirs";
  const path = "products[desk].description";
  assert.deepEqual(mergeCatalog(base, local, remote).conflicts, [{ path, local: "Mine", remote: "Theirs" }]);
  for (const [choice, expected] of [["local", "Mine"], ["remote", "Theirs"]]) {
    const result = mergeCatalog(base, local, remote, { [path]: choice });
    assert.deepEqual(result.conflicts, []);
    assert.equal(result.catalog.products[0].description, expected);
  }
});

test("deletion versus an edit is a conflict and can explicitly keep the deletion", () => {
  const base = catalog(), local = catalog(), remote = catalog();
  local.products.shift();
  remote.products[0].price = 4.99;
  assert.equal(mergeCatalog(base, local, remote).conflicts[0].path, "products[desk]");
  const result = mergeCatalog(base, local, remote, { "products[desk]": "local" });
  assert.deepEqual(result.conflicts, []);
  assert.deepEqual(result.catalog.products.map(p => p.id), ["weather"]);
});

test("merges independent additions and deletions without losing remote entries", () => {
  const base = catalog(), local = catalog(), remote = catalog();
  local.products.pop();
  local.products.push({ id: "local-new" });
  remote.products.push({ id: "remote-new" });
  const result = mergeCatalog(base, local, remote);
  assert.deepEqual(result.conflicts, []);
  assert.deepEqual(new Set(result.catalog.products.map(p => p.id)), new Set(["desk", "local-new", "remote-new"]));
});

test("conflicting image lists are not silently joined and identical edits are accepted", () => {
  const base = catalog(), local = catalog(), remote = catalog();
  local.products[0].images = ["mine.jpg"];
  remote.products[0].images = ["theirs.jpg"];
  assert.equal(mergeCatalog(base, local, remote).conflicts[0].path, "products[desk].images");
  remote.products[0].images = ["mine.jpg"];
  assert.deepEqual(mergeCatalog(base, local, remote).conflicts, []);
});

test("competing reorder operations require a choice and retain independent edits", () => {
  const base = catalog(); base.products.push({ id: "third", price: 1 });
  const local = structuredClone(base), remote = structuredClone(base);
  local.products.reverse();
  remote.products = [remote.products[1], remote.products[0], remote.products[2]];
  local.settings.checkoutEnabled = true;
  assert.equal(mergeCatalog(base, local, remote).conflicts[0].path, "products.order");
  const result = mergeCatalog(base, local, remote, { "products.order": "remote" });
  assert.deepEqual(result.conflicts, []);
  assert.deepEqual(result.catalog.products.map(p => p.id), ["weather", "desk", "third"]);
  assert.equal(result.catalog.settings.checkoutEnabled, true);
});
