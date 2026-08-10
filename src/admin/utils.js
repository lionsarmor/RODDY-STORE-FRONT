export function slugify(name) {
  return (
    String(name)
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "") || `product-${Date.now()}`
  );
}

export function specsToText(specs) {
  return Object.entries(specs || {})
    .map(([k, v]) => `${k}: ${v}`)
    .join("\n");
}

export function textToSpecs(text) {
  const specs = {};
  String(text)
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .forEach((line) => {
      const idx = line.indexOf(":");
      if (idx === -1) return;
      const key = line.slice(0, idx).trim();
      const val = line.slice(idx + 1).trim();
      if (key) specs[key] = val;
    });
  return specs;
}

export function blankProduct(existingIds) {
  let id = "new-product";
  let n = 1;
  while (existingIds.has(id)) id = `new-product-${n++}`;
  return {
    id,
    sku: "R-000",
    name: "New product",
    category: "games",
    price: 0,
    stock: 0,
    active: false,
    featured: false,
    description: "",
    specs: {},
  };
}

export function blankCategory(existingIds) {
  let id = "new-category";
  let n = 1;
  while (existingIds.has(id)) id = `new-category-${n++}`;
  return { id, name: "New category", code: "" };
}
