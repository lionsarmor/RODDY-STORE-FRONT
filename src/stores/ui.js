import { defineStore } from "pinia";

let hideTimer = null;

export const useUiStore = defineStore("ui", {
  state: () => ({
    toastMessage: "",
    toastVisible: false,
    themeOverlayOpen: false,
  }),
  actions: {
    toast(message) {
      this.toastMessage = message;
      this.toastVisible = true;
      clearTimeout(hideTimer);
      hideTimer = setTimeout(() => {
        this.toastVisible = false;
      }, 2200);
    },
    openThemeOverlay() {
      this.themeOverlayOpen = true;
    },
    closeThemeOverlay() {
      this.themeOverlayOpen = false;
    },
  },
});
