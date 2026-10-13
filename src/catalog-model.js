export const DEFAULT_TAGS = [
  { id: "esp32", label: "ESP32", color: "#b9e6f5" },
  { id: "ai-assisted", label: "AI Assisted", color: "#dac6ff" },
  { id: "no-ai", label: "NO AI", color: "#c5e5bd" },
  { id: "free", label: "FREE", color: "#f8da79" },
];

export const DEFAULT_SETTINGS = {
  announcement: "INDEPENDENT TECHNOLOGY. UNREASONABLE POSSIBILITIES.",
  heroEyebrow: "WELCOME TO THE RODDY WORLD",
  heroTitle: "THE FUTURE\nIS PERSONAL.",
  heroDescription:
    "Pocket-sized worlds. Strange new games. Computers with character. Welcome to a different kind of technology company.",
  heroProductId: "keychain-kreatures",
  heroImage: "",
  heroButton: "Explore the catalog",
  featuredTitle: "SMALL CATALOG. BIG IDEAS.",
  manifestoTitle: "LESS DISPOSABLE.\nMORE DISCOVERABLE.",
  manifestoText:
    "We believe technology should invite you in. Push a button. Meet a creature. Make something strange. There is still room for a little wonder.",
  supportEmail: "",
  checkoutEnabled: false,
  checkoutEndpoint: "",
  allowPromotionCodes: true,
  automaticTax: false,
  shippingCountries: "US,CA",
  shippingRate: 0,
  shippingLabel: "Standard shipping",
};

export function normalizeProduct(p) {
  return {
    ...p,
    status: p.status || "available",
    type: p.type || "physical",
    images: Array.isArray(p.images) ? p.images : p.image ? [p.image] : [],
    coverImage: p.coverImage || p.images?.[0] || p.image || "",
    tags: Array.isArray(p.tags) ? p.tags : [],
    trackStock: p.trackStock !== false,
    compareAtPrice: p.compareAtPrice || 0,
    shortDescription: p.shortDescription || "",
    story: p.story || "",
    documentationUrl: p.documentationUrl || "",
    releaseNote: p.releaseNote || "",
    downloadUrl: p.downloadUrl || "",
    githubUrl: p.githubUrl || "",
    officeShipping: p.officeShipping || {},
    supplier: p.supplier || null,
    merch: p.merch ? { ...p.merch, variants: Array.isArray(p.merch.variants) ? p.merch.variants : [], shippingCountries: p.merch.shippingCountries || ["US", "CA"], shippingProfiles: p.merch.shippingProfiles || [] } : null,
  };
}

export function normalizeCatalog(data) {
  return {
    ...data,
    schemaVersion: 2,
    categories: Array.isArray(data.categories) ? data.categories : [],
    products: (data.products || []).map(normalizeProduct),
    tags: Array.isArray(data.tags) ? data.tags : structuredClone(DEFAULT_TAGS),
    settings: { ...DEFAULT_SETTINGS, ...data.settings },
  };
}

export function safeLink(value) {
  try {
    return ["https:", "http:"].includes(new URL(value).protocol) ? value : "";
  } catch {
    return "";
  }
}

export function validateCatalog(data) {
  const errors = [];
  const skus = new Set();
  const supplierKeys = new Set();
  for (const [label, list] of [
    ["Product", data.products],
    ["Category", data.categories],
    ["Tag", data.tags],
  ]) {
    const ids = new Set();
    for (const item of list) {
      if (!/^[a-z0-9][a-z0-9-]*$/.test(item.id) || ids.has(item.id))
        errors.push(`${label} IDs must be unique lowercase slugs: ${item.id}`);
      ids.add(item.id);
      if (!(item.name || item.label)?.trim())
        errors.push(`${label} ${item.id} needs a name.`);
    }
  }
  for (const p of data.products) {
    if (!p.sku?.trim() || skus.has(p.sku.trim().toLowerCase()))
      errors.push(`${p.name}: SKU must be present and unique.`);
    if (p.sku?.trim()) skus.add(p.sku.trim().toLowerCase());
    if (!data.categories.some((c) => c.id === p.category))
      errors.push(`${p.name}: choose a category.`);
    if (
      !Number.isFinite(p.price) ||
      p.price < 0 ||
      Math.round(p.price * 100) > 99999999
    )
      errors.push(`${p.name}: enter a valid price.`);
    if (!Number.isInteger(p.stock) || p.stock < 0)
      errors.push(`${p.name}: stock must be a whole number, zero or more.`);
    if (!["available", "coming-soon", "sold-out"].includes(p.status))
      errors.push(`${p.name}: invalid availability.`);
    if (!["physical", "digital"].includes(p.type))
      errors.push(`${p.name}: invalid product type.`);
    if (
      p.compareAtPrice &&
      (!Number.isFinite(p.compareAtPrice) || p.compareAtPrice <= p.price)
    )
      errors.push(`${p.name}: original price must exceed the selling price.`);
    if (p.tags.some((id) => !data.tags.some((t) => t.id === id)))
      errors.push(`${p.name}: unknown tag.`);
    if (p.tags.includes("ai-assisted") && p.tags.includes("no-ai"))
      errors.push(`${p.name}: choose AI Assisted or NO AI, not both.`);
    if (p.tags.includes("free") && p.price !== 0)
      errors.push(`${p.name}: FREE requires a zero price.`);
    for (const [country, rate] of Object.entries(p.officeShipping || {})) {
      if (!["US", "CA"].includes(country) || !rate || [rate.firstItem, rate.additionalItem].some(n => !Number.isFinite(n) || n < 0 || n > 999999 || Math.abs(n*100-Math.round(n*100)) > .00001))
        errors.push(`${p.name}: enter valid office shipping rates for US or Canada.`);
    }
    if (p.supplier) {
      const s = p.supplier;
      const key = JSON.stringify([s.provider, String(s.supplierSku || "").toLowerCase(), s.variantId || ""]);
      if (!["mouser", "aliexpress"].includes(s.provider) || p.type !== "physical" || p.merch)
        errors.push(`${p.name}: choose one supported physical-product supplier.`);
      if (typeof s.supplierSku !== "string" || !s.supplierSku.trim() || s.supplierSku.length > 80 || supplierKeys.has(key))
        errors.push(`${p.name}: supplier listing and variant must be present and unique.`);
      supplierKeys.add(key);
      if (!["pending", "office"].includes(s.fulfillment)) errors.push(`${p.name}: choose pending or office fulfillment. Direct supplier ordering is not enabled.`);
      if (s.provider === "aliexpress" && (typeof s.variantId !== "string" || !s.variantId)) errors.push(`${p.name}: choose an exact AliExpress variant before importing.`);
      if (s.productUrl && (!safeLink(s.productUrl) || !s.productUrl.startsWith("https://"))) errors.push(`${p.name}: use a valid HTTPS supplier listing URL.`);
      if ([s.minimumQuantity, s.orderMultiple].some(n => !Number.isInteger(n) || n < 1)) errors.push(`${p.name}: supplier minimums must be positive whole numbers.`);
    }
    if (p.merch) {
      const m = p.merch, ids = new Set(), combinations = new Set();
      if (p.type !== "physical" || m.provider !== "printify") errors.push(`${p.name}: Printify requires a physical product.`);
      if (!/^[a-zA-Z0-9_-]{1,80}$/.test(m.productId || "") || !Number.isInteger(m.shopId) || m.shopId < 1)
        errors.push(`${p.name}: import a valid Printify product and store.`);
      for (const v of m.variants) {
        const combo = JSON.stringify([v.color, v.size]);
        if (typeof v.id !== "string" || !v.id || ids.has(v.id) || combinations.has(combo) || !Number.isInteger(v.providerVariantId) || v.providerVariantId < 1)
          errors.push(`${p.name}: variant IDs and color/size combinations must be unique and mapped to Printify.`);
        ids.add(v.id); combinations.add(combo);
        if (!Number.isFinite(v.price) || v.price <= 0 || v.price > 999999 || Math.abs(v.price * 100 - Math.round(v.price * 100)) > .00001)
          errors.push(`${p.name}: every variant needs a valid retail price with at most two decimals.`);
        if (typeof v.enabled !== "boolean" || ![true, false, null].includes(v.available)) errors.push(`${p.name}: invalid variant availability.`);
        if (v.image && !safeLink(v.image)) errors.push(`${p.name}: invalid variant image URL.`);
      }
      if (!m.shippingCountries.length || m.shippingCountries.some(c => !/^[A-Z]{2}$/.test(c))) errors.push(`${p.name}: choose valid shipping countries.`);
      for (const rate of m.shippingProfiles) {
        if (!Array.isArray(rate.variantIds) || !Array.isArray(rate.countries) || [rate.firstItem, rate.additionalItem].some(n => !Number.isFinite(n) || n < 0))
          errors.push(`${p.name}: invalid merchandise shipping rates.`);
      }
    }
    if (p.downloadUrl && !safeLink(p.downloadUrl))
      errors.push(`${p.name}: download must be an HTTP(S) URL.`);
    if (p.downloadUrl && p.price > 0)
      errors.push(
        `${p.name}: paid products must not have a public free-download URL.`,
      );
    if (p.documentationUrl && !safeLink(p.documentationUrl))
      errors.push(`${p.name}: documentation must be an HTTP(S) URL.`);
    if (p.githubUrl && !/^https:\/\/github\.com\//i.test(p.githubUrl))
      errors.push(`${p.name}: use a https://github.com/ repository URL.`);
  }
  for (const t of data.tags)
    if (!/^#[0-9a-f]{6}$/i.test(t.color))
      errors.push(`${t.label}: choose a valid color.`);
  const s = data.settings;
  if (
    s.heroProductId &&
    !data.products.some((p) => p.id === s.heroProductId && p.active)
  )
    errors.push("Choose a visible product for the homepage spotlight.");
  if (s.checkoutEndpoint && !/^https:\/\//.test(s.checkoutEndpoint))
    errors.push("Checkout server must use HTTPS.");
  if (s.checkoutEnabled && !s.checkoutEndpoint)
    errors.push("Add a checkout server URL before enabling checkout.");
  if (!Number.isFinite(s.shippingRate) || s.shippingRate < 0)
    errors.push("Shipping price must be zero or more.");
  if (!/^[A-Z]{2}(\s*,\s*[A-Z]{2})*$/.test(s.shippingCountries))
    errors.push("Use comma-separated country codes, for example US,CA.");
  return errors;
}
