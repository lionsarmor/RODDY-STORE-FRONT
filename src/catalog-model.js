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
    releaseNote: p.releaseNote || "",
    downloadUrl: p.downloadUrl || "",
    githubUrl: p.githubUrl || "",
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
    if (p.downloadUrl && !safeLink(p.downloadUrl))
      errors.push(`${p.name}: download must be an HTTP(S) URL.`);
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
