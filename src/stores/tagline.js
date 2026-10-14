import { defineStore } from "pinia";

// On-page brand lines rotate together. Document and link-preview metadata
// stay fixed so shared links always describe the RODDY storefront consistently.
export const RODDY_TAGLINES = [
  "Play. Build. Make it yours.",
  "Independent technology. Unreasonable possibilities.",
  "Small catalog. Big ideas.",
  "Computers with character.",
  "Strange new games. Good company.",
  "Pocket-sized worlds. Room for wonder.",
  "Made for curious people.",
  "Make something strange.",
  "A little curiosity goes a long way.",
  "Your next good idea starts here.",
  "Tools with personality.",
  "Push a button. See what happens.",
  "For the things you want to make.",
  "Less disposable. More discoverable.",
  "From our workbench to your world.",
  "Play. Build. Program. Keep.",
];

const ROTATE_MS = 30000;

export const useTaglineStore = defineStore("tagline", {
  state: () => ({
    tick: 0,
    started: false,
  }),

  getters: {
    // `tick` is read (not used) purely so this getter re-evaluates on every
    // rotation; the actual line is derived from Date.now() so it's identical
    // for every component/tab reading it at the same moment.
    index: (state) => {
      void state.tick;
      return Math.floor(Date.now() / ROTATE_MS) % RODDY_TAGLINES.length;
    },
    current: (state) => RODDY_TAGLINES[state.index],
  },

  actions: {
    start() {
      if (this.started) return;
      this.started = true;
      // Align the first flip to the next real 30s wall-clock boundary so a
      // tab opened mid-window doesn't drift out of sync with other tabs.
      const delay = ROTATE_MS - (Date.now() % ROTATE_MS);
      setTimeout(() => {
        this.tick++;
        setInterval(() => this.tick++, ROTATE_MS);
      }, delay);
    },
  },
});
