/* RODDY theme registry — lightweight metadata only.
   The full CSS custom-property sets per theme live in src/styles/themes.css
   (that's what Tailwind's color utilities read from at paint time); this
   file just carries what JS/Vue needs: which logo asset to show, and a
   3-color preview swatch for the theme picker.

   "industrial" is the default and is pixel-matched to the literal master
   artwork in public/img/logos/RODDY_SVG_BRAND_PACK/00_ORIGINAL_MASTERS:
   capsule #ded1bf, lettering #000000, dot #c32d28. */

export const RODDY_THEMES = [
  { id: "industrial", group: "CORPORATE", label: "Industrial", sub: "the master — 1982 terminal manufacturer", logo: "classic_cream_red", swatch: ["#ded1bf", "#000000", "#c32d28"] },
  { id: "blueprint", group: "CORPORATE", label: "Blueprint", sub: "spec-sheet white", logo: "white_red", swatch: ["#f5f5f2", "#15161a", "#e5322d"] },
  { id: "neon-cyan", group: "ARCADE", label: "Arcade / Cyan", sub: "launch graphics", logo: "neon_cyan_red", swatch: ["#0a0b0d", "#10d7f4", "#ff2b2b"] },
  { id: "neon-magenta", group: "ARCADE", label: "Arcade / Magenta", sub: "signage & packaging", logo: "neon_magenta_red", swatch: ["#0d0a0d", "#f21a83", "#ff3b35"] },
  { id: "neon-lime", group: "ARCADE", label: "Arcade / Lime", sub: "special edition hardware", logo: "neon_lime_red", swatch: ["#0a0d09", "#82e52d", "#ff382e"] },
  { id: "neon-orange", group: "ARCADE", label: "Arcade / Orange", sub: "advertising", logo: "neon_orange_red", swatch: ["#0d0a09", "#ff7118", "#ff3a28"] },
  { id: "neon-violet", group: "ARCADE", label: "Arcade / Violet", sub: "arcades", logo: "neon_violet_red", swatch: ["#0a0a0d", "#a966ff", "#ff3952"] },
  { id: "field-olive", group: "FIELD", label: "Field / Olive", sub: "1970s instrumentation", logo: "muted_olive_red", swatch: ["#1b1c15", "#72784b", "#c74632"] },
  { id: "field-slate", group: "FIELD", label: "Field / Slate", sub: "portable terminals", logo: "muted_slate_red", swatch: ["#141819", "#536b79", "#c74632"] },
  { id: "field-sand", group: "FIELD", label: "Field / Sand", sub: "government electronics", logo: "muted_sand_red", swatch: ["#e7e0d1", "#a9987d", "#b94a38"] },
  { id: "pocket-mint", group: "POCKET", label: "Pocket / Mint", sub: "Keychain Kreatures", logo: "pastel_mint_pink", swatch: ["#f3faf7", "#9ddccf", "#efa4ae"] },
  { id: "pocket-lavender", group: "POCKET", label: "Pocket / Lavender", sub: "collectible hardware", logo: "pastel_lavender", swatch: ["#f8f4fb", "#b99acf", "#e18cb8"] },
  { id: "pocket-peach", group: "POCKET", label: "Pocket / Peach", sub: "family-friendly games", logo: "pastel_peach_mint", swatch: ["#fbf5f1", "#f2a084", "#8fc6bd"] },
  { id: "collector-gold", group: "COLLECTOR", label: "Collector / Gold", sub: "limited run", logo: "gold_black", swatch: ["#0c0a04", "#f3c51b", "#f3c51b"] },
];

export const RODDY_THEME_IDS = RODDY_THEMES.map((t) => t.id);
export const RODDY_DEFAULT_THEME = "industrial";
export const RODDY_THEME_STORAGE_KEY = "roddy:theme";

export function getRoddyTheme(id) {
  return RODDY_THEMES.find((t) => t.id === id) || RODDY_THEMES[0];
}

const LOGO_STYLE_SUFFIX = { filled: "_filled", outline: "_outline", neon_glow: "_glow" };

export function roddyLogoPath(logoKey, kind, style) {
  // kind: "full_logo" | "badge"
  // style: "filled" | "outline" | "neon_glow"
  const prefix = kind === "badge" ? "roddy_badge_" : "roddy_full_";
  const suffix = LOGO_STYLE_SUFFIX[style];
  const base = import.meta.env.BASE_URL;
  return `${base}img/logos/RODDY_SVG_BRAND_PACK/${kind}/${style}/${prefix}${logoKey}${suffix}.svg`;
}
