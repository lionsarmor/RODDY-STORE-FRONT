// Vite inlines this self-contained function into every HTML entry's head.
// Keep dependencies in the arguments so it runs before CSS and Vue load.
export function bootstrapTheme(themeIds, storageKey) {
  let theme;
  try {
    theme = localStorage.getItem(storageKey);
  } catch {
    // A blocked storage API must not prevent the initial palette applying.
  }

  if (!themeIds.includes(theme)) {
    theme = themeIds[Math.floor(Math.random() * themeIds.length)];
    try {
      localStorage.setItem(storageKey, theme);
    } catch {
      // The palette still works for this visit when persistence is unavailable.
    }
  }

  document.documentElement.setAttribute("data-theme", theme);
}
