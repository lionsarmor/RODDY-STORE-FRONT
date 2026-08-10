import { defineStore } from "pinia";
import {
  RODDY_THEMES,
  RODDY_THEME_IDS,
  RODDY_DEFAULT_THEME,
  RODDY_THEME_STORAGE_KEY,
  getRoddyTheme,
  roddyLogoPath,
} from "../theme-data";

export const useThemeStore = defineStore("theme", {
  state: () => ({
    // The boot script in <head> already set data-theme on <html> before Vue
    // mounted (from localStorage, or left as the default) — read it back so
    // the store's reactive state matches what's already painted, with no flash.
    currentId: document.documentElement.getAttribute("data-theme") || RODDY_DEFAULT_THEME,
  }),

  getters: {
    current: (state) => getRoddyTheme(state.currentId),
    themes: () => RODDY_THEMES,
    grouped: () => {
      const groups = {};
      RODDY_THEMES.forEach((t) => {
        groups[t.group] = groups[t.group] || [];
        groups[t.group].push(t);
      });
      return groups;
    },
  },

  actions: {
    apply(id, opts = {}) {
      const theme = getRoddyTheme(id);
      this.currentId = theme.id;
      document.documentElement.setAttribute("data-theme", theme.id);
      try {
        localStorage.setItem(RODDY_THEME_STORAGE_KEY, theme.id);
      } catch (e) {
        /* storage unavailable, theme just won't persist */
      }
      if (!opts.silent) this.flash();
    },

    cycle() {
      const idx = RODDY_THEME_IDS.indexOf(this.currentId);
      this.apply(RODDY_THEME_IDS[(idx + 1) % RODDY_THEME_IDS.length]);
    },

    flash() {
      document.body.classList.remove("roddy-theme-flash");
      void document.body.offsetWidth; // restart the animation
      document.body.classList.add("roddy-theme-flash");
    },

    logoSrc(kind = "full_logo") {
      // CORPORATE (industrial, blueprint) keeps the black-ring outline mark;
      // ARCADE glows; everything else uses the solid filled mark.
      const group = this.current.group;
      const style = group === "CORPORATE" ? "outline" : group === "ARCADE" ? "neon_glow" : "filled";
      return roddyLogoPath(this.current.logo, kind, style);
    },
  },
});
