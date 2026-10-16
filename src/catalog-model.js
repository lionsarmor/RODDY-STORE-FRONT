import { shippingCountries } from './shipping-destinations.js';
import { PRODUCT_ORIGINS } from './product-origin.js';
import {catalogColorId} from './keycap-palette.js';
import { KEYCAP_PREVIEWS, MARKS, DISABLED_MARKS, ARROWS, NUMBER_ROWS, defaultDesign, designError } from './keycaps.js';

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
    designOrigin: p.designOrigin || 'selected',
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
    fulfillment: p.fulfillment || "",
    pricingMode: p.pricingMode || "automatic",
    pricingFloor: p.pricingFloor || 0,
    fulfillmentRef: p.fulfillmentRef || "",
    keycaps: p.keycaps || null,
    merch: p.merch ? { ...p.merch, variants: Array.isArray(p.merch.variants) ? p.merch.variants : [], shippingCountries: p.merch.shippingCountries || ["US", "CA"], shippingProfiles: p.merch.shippingProfiles || [] } : null,
  };
}

export function normalizeCatalog(data) {
  return {
    ...data,
    schemaVersion: 2,
    keycapProfiles: Array.isArray(data.keycapProfiles) ? data.keycapProfiles.map(profile=>{
      const clean={...profile,numberRows:profile.numberRows || KEYCAP_PREVIEWS[profile.templateId]?.numberRows || ['swatches','text'],marks:profile.marks?.filter(id=>!DISABLED_MARKS.includes(id)),defaults:{numberRow:'swatches',...profile.defaults,keyColors:profile.defaults?.keyColors || {}}};
      for(const group of ['alpha','modifiers','accents'])clean.defaults[group]=catalogColorId(clean.defaults[group]);
      if(DISABLED_MARKS.includes(clean.defaults?.mark))clean.defaults={...clean.defaults,mark:defaultDesign(clean).mark};
      return clean;
    }) : [],
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

export function customerLink(value) {
  if (!safeLink(value)) return "";
  const host = new URL(value).hostname;
  return /(^|\.)(github\.com|githubusercontent\.com|github\.io)$/i.test(host) ? "" : value;
}

export function pdfDocumentation(value) {
  return customerLink(value) && /\.pdf$/i.test(new URL(value).pathname) ? value : "";
}

export function validateCatalog(data) {
  const errors = [];
  const skus = new Set();
  const supplierKeys = new Set();
  for (const [label, list] of [
    ["Product", data.products],
    ["Category", data.categories],
    ["Tag", data.tags],
    ["Keyboard profile", data.keycapProfiles || []],
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
  for (const profile of data.keycapProfiles || []) {
    if (!KEYCAP_PREVIEWS[profile.templateId] || !/^[a-zA-Z0-9._-]{1,40}$/.test(profile.revision || '')) errors.push(`${profile.name}: choose a validated template and revision.`);
    if (!Array.isArray(profile.marks) || !profile.marks.length || profile.marks.some(id=>!MARKS[id]) || !Array.isArray(profile.arrows) || !profile.arrows.length || profile.arrows.some(id=>!ARROWS[id])) errors.push(`${profile.name}: choose supported symbols and arrows.`);
    if (!Array.isArray(profile.numberRows) || !profile.numberRows.length || profile.numberRows.some(id=>!NUMBER_ROWS[id])) errors.push(`${profile.name}: choose supported number-row legends.`);
    if (designError(defaultDesign(profile),profile)) errors.push(`${profile.name}: check profile defaults.`);
  }
  for (const p of data.products) {
    if (p.designOrigin && !PRODUCT_ORIGINS.some(origin => origin.id === p.designOrigin)) errors.push(`${p.name}: choose a supported design credit.`);
    if (p.keycaps && (p.type !== 'physical' || p.merch || p.supplier || p.trackStock !== false || !(data.keycapProfiles || []).some(profile=>profile.id===p.keycaps.profileId))) errors.push(`${p.name}: choose a valid keyboard profile, physical product and made-to-order stock mode.`);
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
    if (p.active && p.status === 'available' && p.pricePending) errors.push(`${p.name}: set a final price before marking this product available, or choose Coming soon.`);
    if (p.active && p.status === 'available' && (p.supplier?.fulfillment || p.fulfillment) === 'pending') errors.push(`${p.name}: choose a ready fulfillment mode before marking this product available.`);
    if (p.shippingCountries !== undefined && (!Array.isArray(p.shippingCountries) || !p.shippingCountries.length || p.shippingCountries.some(c => !['US','CA'].includes(c)) || new Set(p.shippingCountries).size !== p.shippingCountries.length)) errors.push(`${p.name}: choose supported shipping destinations.`);
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
    if (!['automatic','fixed'].includes(p.pricingMode) || !Number.isFinite(p.pricingFloor) || p.pricingFloor<0 || Math.abs(p.pricingFloor*100-Math.round(p.pricingFloor*100))>.000001) errors.push(`${p.name}: check automatic pricing mode and minimum price.`);
    if (p.supplier) {
      const s = p.supplier;
      const key = JSON.stringify([s.provider, String(s.supplierSku || "").toLowerCase(), s.variantId || ""]);
      if (!["mouser", "aliexpress"].includes(s.provider) || p.type !== "physical" || p.merch)
        errors.push(`${p.name}: choose one supported physical-product supplier.`);
      if (typeof s.supplierSku !== "string" || !s.supplierSku.trim() || s.supplierSku.length > 80 || supplierKeys.has(key))
        errors.push(`${p.name}: supplier listing and variant must be present and unique.`);
      supplierKeys.add(key);
      if (!["pending", "office", "manual", "automatic"].includes(s.fulfillment)) errors.push(`${p.name}: choose a supported fulfillment mode.`);
      if (s.fulfillment==='automatic' && s.provider!=='mouser') errors.push(`${p.name}: automatic ordering is not connected for this supplier.`);
      if (s.provider === "aliexpress" && (typeof s.variantId !== "string" || !s.variantId)) errors.push(`${p.name}: choose an exact AliExpress variant before importing.`);
      if (s.productUrl && (!safeLink(s.productUrl) || !s.productUrl.startsWith("https://"))) errors.push(`${p.name}: use a valid HTTPS supplier listing URL.`);
      if ([s.minimumQuantity, s.orderMultiple].some(n => !Number.isInteger(n) || n < 1)) errors.push(`${p.name}: supplier minimums must be positive whole numbers.`);
      if (s.bom !== undefined) {
        const b = s.bom, seen = new Set();
        if (s.provider !== 'mouser' || s.fulfillment !== 'automatic' || !b || !['draft','ready'].includes(b.status) || !Array.isArray(b.lines) || b.lines.length > 250) {
          errors.push(`${p.name}: use a valid automatic Mouser kit BOM.`);
        } else {
          if (b.status === 'ready' && (!/^[A-Za-z0-9._-]{1,80}$/.test(b.revision || '') || !b.lines.length)) errors.push(`${p.name}: a complete BOM needs a revision and exact part lines.`);
          for (const line of b.lines) {
            if (!line || !/^[A-Za-z0-9][A-Za-z0-9./_()+#-]{0,79}$/.test(line.supplierSku || '') || seen.has(line.supplierSku) || !Number.isInteger(line.quantity) || line.quantity < 1 || line.quantity > 10000) errors.push(`${p.name}: BOM lines need unique exact Mouser numbers and whole order-unit quantities.`);
            seen.add(line?.supplierSku);
          }
          if (p.active && p.status === 'available' && b.status !== 'ready') errors.push(`${p.name}: finish the parts list before enabling kit purchases. Incomplete physical testing can be disclosed with the red warning.`);
        }
      }
    }
    if (p.merch) {
      const m = p.merch, ids = new Set(), combinations = new Set();
      if (p.type !== "physical" || !["printify","custom"].includes(m.provider)) errors.push(`${p.name}: Printify requires a physical product.`);
      if (m.provider!=="custom" && (!/^[a-zA-Z0-9_-]{1,80}$/.test(m.productId || "") || !Number.isInteger(m.shopId) || m.shopId < 1))
        errors.push(`${p.name}: import a valid Printify product and store.`);
      for (const v of m.variants) {
        const combo = JSON.stringify([v.color, v.size]);
        if (typeof v.id !== "string" || !v.id || ids.has(v.id) || combinations.has(combo) || (m.provider!=="custom" && (!Number.isInteger(v.providerVariantId) || v.providerVariantId < 1)))
          errors.push(`${p.name}: variant IDs and color/size combinations must be unique and mapped to Printify.`);
        ids.add(v.id); combinations.add(combo);
        if (!Number.isFinite(v.price) || v.price <= 0 || v.price > 999999 || Math.abs(v.price * 100 - Math.round(v.price * 100)) > .00001)
          errors.push(`${p.name}: every variant needs a valid retail price with at most two decimals.`);
        if (typeof v.enabled !== "boolean" || ![true, false, null].includes(v.available)) errors.push(`${p.name}: invalid variant availability.`);
        if (v.image && !safeLink(v.image) && !(/^img\/[a-zA-Z0-9_./-]+\.(png|jpe?g|webp|svg)$/i.test(v.image) && !v.image.split('/').includes('..'))) errors.push(`${p.name}: invalid variant image URL.`);
      }
      if (!m.shippingCountries.length || m.shippingCountries.some(c => !/^[A-Z]{2}$/.test(c))) errors.push(`${p.name}: choose valid shipping countries.`);
      for (const rate of m.shippingProfiles) {
        if (!Array.isArray(rate.variantIds) || !Array.isArray(rate.countries) || [rate.firstItem, rate.additionalItem].some(n => !Number.isFinite(n) || n < 0))
          errors.push(`${p.name}: invalid merchandise shipping rates.`);
      }
    }
    if (p.type === 'physical' && p.active && p.status === 'available') {
      const countries = shippingCountries(p);
      if (!countries.length) errors.push(`${p.name}: enable at least one shipping destination.`);
      const liveShipping = p.merch || (p.supplier?.provider === 'aliexpress' && p.supplier.fulfillment === 'manual') || (!p.supplier && p.fulfillment === 'manual');
      if (!liveShipping && (p.supplier?.fulfillment || p.fulfillment)!=='automatic' && countries.some(c => !p.officeShipping?.[c])) errors.push(`${p.name}: add a shipping rate for each enabled destination.`);
    }
    if (p.downloadUrl && !safeLink(p.downloadUrl))
      errors.push(`${p.name}: download must be an HTTP(S) URL.`);
    else if (p.downloadUrl && !customerLink(p.downloadUrl))
      errors.push(`${p.name}: host customer downloads on the storefront, not GitHub.`);
    if (p.downloadUrl && p.price > 0)
      errors.push(
        `${p.name}: paid products must not have a public free-download URL.`,
      );
    if (p.documentationUrl && !safeLink(p.documentationUrl))
      errors.push(`${p.name}: documentation must be an HTTP(S) URL.`);
    else if (p.documentationUrl && !customerLink(p.documentationUrl))
      errors.push(`${p.name}: host customer documentation on the storefront, not GitHub.`);
    else if (p.category === 'labs' && p.documentationUrl && !pdfDocumentation(p.documentationUrl))
      errors.push(`${p.name}: Labs documentation must link directly to a PDF.`);
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
