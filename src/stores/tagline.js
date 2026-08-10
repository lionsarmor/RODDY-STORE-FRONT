import { defineStore } from "pinia";

// Every place the old "modern technology from a future we were promised"
// line used to live now pulls from this list instead. The index is derived
// from wall-clock time (not a per-component timer), so every instance across
// the page — hero, footer, about, document title — flips to the same line
// at the same moment without any coordination between components.
export const RODDY_TAGLINES = [
  "Tomorrow, as advertised. ⭐",
  "Tomorrow, rebooted.",
  "Tomorrow was canceled.",
  "Tomorrow: Now with 16 colors!",
  "Tomorrow has a Turbo button.",
  "Tomorrow. No subscription required. 🔥",
  "Tomorrow used to come with a manual.",
  "Tomorrow comes with instructions.",
  "Tomorrow. Batteries not included.",
  "Tomorrow, sold separately.",
  "Tomorrow is user-serviceable.",
  "Tomorrow works offline.",
  "Tomorrow has actual buttons.",
  "Tomorrow doesn't require an account.",
  "Tomorrow ships on physical media.",
  "Tomorrow comes in a box.",
  "Tomorrow has an OFF switch.",
  "Tomorrow boots in seconds.",
  "Tomorrow. Insert disk to continue.",
  "Tomorrow requires 64K.",
  "Tomorrow is backwards compatible.",
  "Tomorrow has expansion slots.",
  "Tomorrow comes with a warranty card.",
  "Tomorrow looks better in 4:3.",
  "Tomorrow never needed the cloud.",
  "Tomorrow belongs to the user.",
  "Tomorrow is yours to open.",
  "Tomorrow. Some assembly required.",
  "Tomorrow, without the monthly fee.",
  "Tomorrow. Now available offline.",
  "Tomorrow is not a service.",
  "Tomorrow is something you own.",
  "Tomorrow comes with screws.",
  "Tomorrow wasn't supposed to be disposable.",
  "Tomorrow was supposed to be fun.",
  "Tomorrow was supposed to have buttons.",
  "Tomorrow was worth waiting for.",
  "Tomorrow arrived on a floppy.",
  "Tomorrow called. We answered.",
  "Tomorrow is loading...",
  "Tomorrow starts with READY.",
  "Tomorrow. READY.",
  "READY for tomorrow.",
  "Turn on tomorrow.",
  "Boot tomorrow.",
  "Insert tomorrow. Press START.",
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
