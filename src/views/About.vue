<script setup>
import { computed, ref } from "vue";
import RoddyLogo from "../components/RoddyLogo.vue";
import { useUiStore } from "../stores/ui";

const ui = useUiStore();
const expression = ref(0);
const faces = [
  [
    "00100100",
    "00011000",
    "01111110",
    "11011011",
    "11111111",
    "10100101",
    "00111100",
    "01000010",
  ],
  [
    "00100100",
    "00011000",
    "01111110",
    "11011111",
    "11111111",
    "10100101",
    "00111100",
    "01000010",
  ],
  [
    "00000000",
    "01100110",
    "11111111",
    "11111111",
    "01111110",
    "00111100",
    "00011000",
    "00000000",
  ],
];
const pixels = computed(() => faces[expression.value].join("").split(""));
const messages = [
  "READY. YOUR MOVE.",
  "HELLO, HUMAN.",
  "SMALL MACHINE. BIG FEELINGS.",
];
const principles = [
  {
    number: "01",
    title: "Give your attention back.",
    text: "A good machine can do one thing beautifully. A game worth getting lost in. A tool that helps you finish a thought. A little world with edges, so you can put it down and return to your own.",
    footer: "LESS FEED. MORE FOCUS.",
  },
  {
    number: "02",
    title: "Make the limits interesting.",
    text: "A few colors. A tiny screen. A modest chip. Constraints turn a project into a puzzle. We love the clever trick, the unexpected sound, the whole personality hiding in a handful of pixels.",
    footer: "SMALL RESOURCES. BIG IDEAS.",
  },
  {
    number: "03",
    title: "Leave room for the human.",
    text: "We want technology that invites questions. What does this button do? How does this work? What could I make with it? There is something wonderful about a machine you can begin to understand.",
    footer: "CURIOSITY IS A FEATURE.",
  },
];
</script>

<template>
  <article class="about-world">
    <div class="about-masthead">
      <span>RODDY / THE COMPANY WE WANT TO KEEP</span>
      <span>FIELD NOTES ON A DIFFERENT FUTURE</span>
    </div>

    <header class="about-hero">
      <div class="about-hero-copy">
        <p class="eyebrow">
          <span class="status-dot" /> A COMPANY FOR THE CURIOUS
        </p>
        <h1>LESS NOISE.<br />MORE <em>WONDER.</em></h1>
        <p class="about-deck">
          We love retro. We love the future. And we think the best technology
          still leaves room for <strong>you.</strong>
        </p>
        <p class="about-hero-note">
          A FEW WORDS FROM RODDY. ABOUT FOUR MINUTES OF YOUR UNDIVIDED
          ATTENTION.
        </p>
      </div>

      <div class="about-little-machine">
        <div class="about-machine-heading">
          <RoddyLogo kind="badge" />
          <span>DEPARTMENT OF<br />SMALL POSSIBILITIES</span>
        </div>
        <div class="about-pixel-screen">
          <span class="about-screen-label">PERSONALITY / 8 × 8</span>
          <div
            class="about-pixel-face"
            role="img"
            :aria-label="
              expression === 2
                ? 'A heart drawn in 64 pixels'
                : expression === 1
                  ? 'A friendly pixel creature winking'
                  : 'A friendly creature drawn in 64 pixels'
            "
          >
            <span
              v-for="(pixel, i) in pixels"
              :key="i"
              :class="{ lit: pixel === '1' }"
              aria-hidden="true"
            />
          </div>
          <p aria-live="polite">{{ messages[expression] }}</p>
        </div>
        <div class="about-machine-controls">
          <p>64 pixels.<br /><strong>Still a whole personality.</strong></p>
          <button
            class="button"
            @click="expression = (expression + 1) % faces.length"
          >
            Say hello ↗
          </button>
        </div>
      </div>
    </header>

    <div class="spectrum-band" aria-hidden="true">
      <i v-for="n in 6" :key="n" />
    </div>

    <section
      class="about-chapter about-introduction"
      aria-labelledby="about-origin"
    >
      <div class="about-margin-note">
        <span>01 / THE FEELING</span><span>REMEMBER<br />WONDERING?</span>
      </div>
      <div class="about-reading">
        <h2 id="about-origin">
          The future used to feel<br />like something you could touch.
        </h2>
        <p>
          A box on a shelf. A cartridge clicking into place. A blinking cursor,
          waiting patiently for your next idea. A computer that felt like a
          beginning.
        </p>
        <p>
          We love that feeling. The manuals with diagrams. The strange little
          peripherals. The games that built enormous worlds inside tiny amounts
          of memory. Technology had a personality, and getting to know it was
          part of the fun.
        </p>
        <p>
          We love what comes next, too. New chips. Experimental machines.
          Unlikely combinations. Something nobody has quite figured out what to
          call yet. <strong>RODDY is where those two loves meet.</strong>
        </p>
      </div>
    </section>

    <section class="about-statement" aria-labelledby="about-limits">
      <p class="eyebrow">OUR FAVORITE KIND OF TECHNICAL CHALLENGE</p>
      <h2 id="about-limits">
        LIMITED HARDWARE.<br /><span>UNLIMITED “WHAT IF?”</span>
      </h2>
      <div class="about-statement-bottom">
        <span class="about-statement-marker" aria-hidden="true">↗</span>
        <p>A smaller machine can leave a bigger space for imagination.</p>
        <span class="eyebrow">PLAY · BUILD · PROGRAM · KEEP</span>
      </div>
    </section>

    <section class="about-beliefs" aria-labelledby="about-beliefs-title">
      <div class="about-section-heading">
        <p class="eyebrow">02 / THINGS WE BELIEVE</p>
        <h2 id="about-beliefs-title">
          A little less.<br />A lot more possibility.
        </h2>
      </div>
      <div class="about-principles">
        <section
          v-for="principle in principles"
          :key="principle.number"
          class="about-principle"
        >
          <span class="about-principle-number"
            >{{ principle.number }}<span aria-hidden="true">↗</span></span
          >
          <h3>{{ principle.title }}</h3>
          <p>{{ principle.text }}</p>
          <small>{{ principle.footer }}</small>
        </section>
      </div>
    </section>

    <section
      class="about-chapter about-human"
      aria-labelledby="about-human-title"
    >
      <div class="about-margin-note">
        <span>03 / THE HUMAN PART</span><RoddyLogo kind="badge" /><span
          >YOU ARE STILL<br />THE MAIN CHARACTER.</span
        >
      </div>
      <div class="about-reading">
        <h2 id="about-human-title">You don’t need more<br />of everything.</h2>
        <p>
          We don’t think an interesting idea should require an ever more
          expensive pile of RAM. Or that every quiet moment needs a
          notification, every tool needs a subscription, and every machine needs
          to think for you.
        </p>
        <p>
          AI can be a tool. It doesn’t have to be the main character. However
          clever technology becomes, we want the person using it to stay
          curious, capable, and in charge.
        </p>
        <p>
          Sometimes a simpler time is something you can make for yourself, right
          now. Switch on a small machine. Learn its limits. Get good at
          something. Make something odd. Enjoy a game that ends.
          <strong>Let one thing be enough for a while.</strong>
        </p>
        <blockquote>
          “What can we do with this?”<br /><span
            >That’s where the fun starts.</span
          >
        </blockquote>
      </div>
    </section>

    <section
      class="about-chapter about-transparency"
      aria-labelledby="about-transparency-title"
    >
      <div class="about-margin-note">
        <span>04 / NOTHING TO HIDE</span>
        <span>HONEST LABELS.<br />YOUR CHOICE.</span>
      </div>
      <div class="about-reading">
        <h2 id="about-transparency-title">
          How it’s made<br />shouldn’t be a mystery.
        </h2>
        <p>
          Some people are curious about AI. Others would rather have nothing to
          do with it, including in the products they buy. We respect that. You
          shouldn’t have to share our choice of tools to feel welcome here.
        </p>
        <p>
          <strong
            >If AI helped us make a product, we’ll clearly label it AI
            Assisted.</strong
          >
          That includes help with code, artwork, writing, or design. We won’t
          bury that information in the fine print, and we won’t use a
          <strong>NO AI</strong> label unless we can stand behind it. AI
          assistance during creation doesn’t necessarily mean a product runs AI;
          if AI is part of what the product does, we’ll explain that too.
        </p>
        <p>
          We hope to offer a mix of AI-assisted projects and things made without
          AI assistance. Not every project needs the same tools, and not every
          person wants the same thing. Either way,
          <strong>the responsibility for what we release is ours.</strong> A
          tool doesn’t get the credit for caring, or take the blame when
          something needs fixing.
        </p>
        <p>
          We want to be a company you can trust, not one you have to
          second-guess. That means being honest about how we work and giving you
          enough information to choose what feels right for you. No judgment. No
          sales pitch about why you should feel differently.
        </p>
      </div>
    </section>

    <section class="about-repair-promise" aria-labelledby="about-repair-title">
      <div class="about-promise-heading">
        <p class="eyebrow">05 / THE RODDY REPAIR PROMISE</p>
        <RoddyLogo kind="badge" />
      </div>
      <h2 id="about-repair-title">
        MADE FOR HUMAN BEINGS.<br />REPAIRABLE BY HUMAN BEINGS.
      </h2>
      <div class="about-promise-body">
        <div>
          <p>
            Our products are for people. And the knowledge to understand,
            maintain, and repair them belongs with the people who own them.
          </p>
          <p>
            <strong
              >We promise to always include schematics, technical documentation,
              and repair information with our hardware.</strong
            >
            You should be able to find out what’s inside, understand how it
            works, and give it another chapter when something wears out.
          </p>
          <p>
            A repairable machine has a future. We want you to be part of it.
          </p>
        </div>
        <ul
          class="about-promise-inclusions"
          aria-label="Included with RODDY hardware"
        >
          <li>
            <span aria-hidden="true">↗</span>
            <div>
              <strong>SCHEMATICS</strong
              ><small>See how it fits together.</small>
            </div>
          </li>
          <li>
            <span aria-hidden="true">↗</span>
            <div>
              <strong>TECHNICAL DOCUMENTATION</strong
              ><small>Understand what makes it work.</small>
            </div>
          </li>
          <li>
            <span aria-hidden="true">↗</span>
            <div>
              <strong>REPAIR INFORMATION</strong
              ><small>Keep a good thing going.</small>
            </div>
          </li>
        </ul>
      </div>
      <p class="about-promise-seal">
        YOUR MACHINE. YOUR UNDERSTANDING. YOUR RIGHT TO KEEP IT RUNNING.
      </p>
    </section>

    <section class="about-invitation" aria-labelledby="about-invitation-title">
      <div>
        <p class="eyebrow">06 / WELCOME TO OUR CORNER OF THE FUTURE</p>
        <h2 id="about-invitation-title">
          FOR THE TINKERERS.<br />THE DAYDREAMERS.<br />THE
          <em>“WHAT IF?”</em> PEOPLE.
        </h2>
        <p>
          Games, apps, pocket companions, computers, and experiments with a life
          of their own. That’s the world we’re building. If any of this sounds
          like your kind of strange, make yourself at home.
        </p>
        <div class="about-invitation-actions">
          <RouterLink to="/shop" class="button primary"
            >Explore the RODDY world ↗</RouterLink
          >
          <button class="text-button" @click="ui.openThemeOverlay()">
            Find your colorway ◧
          </button>
        </div>
      </div>
      <div class="about-signoff">
        <RoddyLogo kind="full_logo" />
        <span>RETRO HEART.<br />FUTURE FACING.<br />HUMAN OPERATED.</span>
        <small>THANKS FOR READING.<br />NOW GO MAKE SOMETHING.</small>
      </div>
    </section>
  </article>
</template>

<style scoped>
.about-world {
  --about-rule: color-mix(in srgb, var(--color-text) 24%, transparent);
  max-width: 1280px;
  margin-inline: auto;
}
.about-masthead {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 32px;
  border-bottom: 1px solid var(--about-rule);
  font: 9px/1.5 var(--font-mono);
  letter-spacing: 0.08em;
}
.about-hero {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 55px;
  align-items: center;
  padding: 65px 32px 70px;
}
.about-hero h1 {
  font: 900 clamp(48px, 6.5vw, 88px)/0.98 var(--font-sans);
  letter-spacing: -0.065em;
  margin: 30px 0;
}
.about-hero h1 em,
.about-invitation h2 em {
  font-style: normal;
  color: var(--color-text);
  text-decoration: underline;
  text-decoration-color: var(--color-brand);
  text-decoration-thickness: 5px;
  text-underline-offset: 8px;
}
.about-deck {
  max-width: 38ch;
  font-size: 21px;
  line-height: 1.65;
  color: var(--color-text-dim);
}
.about-deck strong {
  color: var(--color-text);
  font-weight: 650;
}
.about-hero-note {
  font: 8px/1.8 var(--font-mono);
  letter-spacing: 0.06em;
  max-width: 49ch;
  margin-top: 38px;
  color: var(--color-text-dim);
}
.about-little-machine {
  border: 1px solid var(--color-text);
  padding: 19px;
  background: var(--color-panel);
  box-shadow: 8px 8px 0 var(--about-rule);
  transform: rotate(2deg);
  min-width: 0;
}
.about-machine-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
  gap: 20px;
}
.about-machine-heading .roddy-logo {
  width: 63px;
  height: auto;
}
.about-machine-heading > span {
  font: 8px/1.7 var(--font-mono);
  text-align: right;
  letter-spacing: 0.08em;
}
.about-pixel-screen {
  border: 1px solid var(--about-rule);
  background: var(--color-bg);
  padding: 18px;
}
.about-screen-label {
  font: 8px var(--font-mono);
  letter-spacing: 0.12em;
  color: var(--color-text-dim);
}
.about-pixel-face {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 4px;
  width: min(75%, 200px);
  aspect-ratio: 1;
  margin: 28px auto;
}
.about-pixel-face span {
  background: color-mix(in srgb, var(--color-text) 5%, transparent);
}
.about-pixel-face .lit {
  background: var(--color-text);
}
.about-pixel-screen p {
  font: 8px/1.8 var(--font-mono);
  letter-spacing: 0.05em;
  min-height: 1.8em;
}
.about-machine-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  margin-top: 18px;
}
.about-machine-controls p {
  font: 9px/1.8 var(--font-mono);
}
.about-machine-controls strong {
  font-weight: 500;
  color: var(--color-text-dim);
}
.about-machine-controls .button {
  font-size: 9px;
  padding: 10px 12px;
  gap: 8px;
  white-space: nowrap;
}
.about-chapter {
  display: grid;
  grid-template-columns: 1fr 3fr;
  gap: 45px;
  padding: 78px 70px 78px 32px;
}
.about-margin-note {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 40px;
  font: 9px/1.8 var(--font-mono);
  letter-spacing: 0.07em;
  color: var(--color-text-dim);
  padding-top: 6px;
}
.about-margin-note > span:last-child {
  font-size: 12px;
  letter-spacing: 0.03em;
  color: var(--color-text);
}
.about-margin-note .roddy-logo {
  width: 80px;
  height: auto;
}
.about-reading {
  max-width: 64ch;
}
.about-reading h2 {
  font: 750 clamp(28px, 3.3vw, 42px)/1.15 var(--font-sans);
  letter-spacing: -0.045em;
  margin-bottom: 28px;
}
.about-reading p {
  font-size: 17px;
  line-height: 1.9;
  color: var(--color-text-dim);
  margin-bottom: 20px;
}
.about-reading p:last-child {
  margin-bottom: 0;
}
.about-reading strong {
  color: var(--color-text);
  font-weight: 650;
}
.about-statement {
  background: var(--color-accent);
  color: var(--color-accent-text);
  padding: 50px 45px 28px;
}
.about-statement h2 {
  font: 850 clamp(32px, 5.4vw, 70px)/1.04 var(--font-sans);
  letter-spacing: -0.055em;
  margin: 30px 0 40px;
}
.about-statement h2 > span {
  font-weight: 400;
}
.about-statement-bottom {
  border-top: 1px solid currentColor;
  padding-top: 20px;
  display: flex;
  gap: 22px;
  align-items: center;
}
.about-statement-marker {
  font-size: 38px;
  line-height: 1;
}
.about-statement-bottom p {
  font-size: 14px;
  max-width: 38ch;
  line-height: 1.6;
}
.about-statement-bottom .eyebrow {
  margin-left: auto;
  font-size: 8px;
}
.about-beliefs {
  padding: 70px 32px;
}
.about-section-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 25px;
  margin-bottom: 32px;
}
.about-section-heading h2 {
  font: 750 33px/1.1 var(--font-sans);
  letter-spacing: -0.045em;
}
.about-principles {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border: 1px solid var(--about-rule);
}
.about-principle {
  padding: 30px 25px 22px;
  background: var(--color-panel);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--about-rule);
}
.about-principle:last-child {
  border-right: 0;
}
.about-principle-number {
  font: 26px var(--font-mono);
  display: flex;
  justify-content: space-between;
  color: var(--color-text-dim);
}
.about-principle-number > span {
  color: var(--color-brand);
}
.about-principle h3 {
  font: 750 25px/1.15 var(--font-sans);
  letter-spacing: -0.04em;
  max-width: 14ch;
  margin: 42px 0 20px;
}
.about-principle p {
  font-size: 14px;
  line-height: 1.85;
  color: var(--color-text-dim);
  margin-bottom: 30px;
}
.about-principle small {
  border-top: 1px solid var(--about-rule);
  padding-top: 17px;
  font: 8px/1.5 var(--font-mono);
  letter-spacing: 0.06em;
  margin-top: auto;
}
.about-human,
.about-transparency {
  border-top: 1px solid var(--about-rule);
  padding-top: 70px;
}
.about-reading blockquote {
  border-left: 3px solid var(--color-brand);
  padding-left: 25px;
  margin: 35px 0 0;
  font: 650 27px/1.4 var(--font-sans);
  letter-spacing: -0.035em;
}
.about-reading blockquote span {
  font-size: 20px;
  font-weight: 400;
  color: var(--color-text-dim);
}
.about-repair-promise {
  margin: 0 32px 70px;
  border: 2px solid var(--color-text);
  background: var(--color-panel);
  padding: 35px;
  box-shadow: 7px 7px 0 var(--about-rule);
}
.about-promise-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  margin-bottom: 30px;
}
.about-promise-heading .roddy-logo {
  width: 65px;
  height: auto;
}
.about-repair-promise h2 {
  font: 800 clamp(27px, 3.4vw, 45px)/1.12 var(--font-sans);
  letter-spacing: -0.05em;
  margin-bottom: 30px;
}
.about-promise-body {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 45px;
}
.about-promise-body p {
  font-size: 16px;
  line-height: 1.85;
  color: var(--color-text-dim);
  margin-bottom: 17px;
}
.about-promise-body p strong {
  color: var(--color-text);
  font-weight: 650;
}
.about-promise-inclusions {
  list-style: none;
  margin: 0;
  padding: 0;
}
.about-promise-inclusions li {
  border-top: 1px solid var(--about-rule);
  padding: 20px 0;
  display: flex;
  gap: 18px;
  align-items: center;
}
.about-promise-inclusions li > span {
  font-size: 25px;
  color: var(--color-brand);
}
.about-promise-inclusions strong {
  display: block;
  font: 500 11px/1.6 var(--font-mono);
}
.about-promise-inclusions small {
  font-size: 12px;
  line-height: 1.7;
  color: var(--color-text-dim);
  display: block;
  margin-top: 5px;
}
.about-promise-seal {
  border-top: 1px solid var(--about-rule);
  padding-top: 20px;
  margin-top: 15px;
  font: 9px/1.8 var(--font-mono);
  letter-spacing: 0.06em;
}
.about-invitation {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 65px;
  padding: 55px 45px;
  border-top: 1px solid var(--color-text);
  background: var(--color-bg-alt);
}
.about-invitation h2 {
  font: 850 clamp(32px, 4vw, 49px)/1.08 var(--font-sans);
  letter-spacing: -0.055em;
  margin: 25px 0;
}
.about-invitation h2 em {
  text-decoration-thickness: 3px;
  text-underline-offset: 4px;
}
.about-invitation p:not(.eyebrow) {
  font-size: 15px;
  line-height: 1.9;
  color: var(--color-text-dim);
  max-width: 50ch;
}
.about-invitation-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 25px;
  margin-top: 30px;
}
.about-signoff {
  border-left: 1px solid var(--about-rule);
  padding: 18px 0 0 40px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.about-signoff .roddy-logo {
  width: min(100%, 210px);
  height: auto;
}
.about-signoff > span {
  font: 500 14px/1.85 var(--font-mono);
  margin-top: 40px;
}
.about-signoff small {
  font: 9px/1.8 var(--font-mono);
  letter-spacing: 0.07em;
  margin-top: auto;
  padding-top: 50px;
  color: var(--color-text-dim);
}
@media (max-width: 1000px) {
  .about-hero {
    gap: 30px;
  }
  .about-hero h1 {
    font-size: clamp(44px, 6.5vw, 68px);
  }
  .about-machine-controls {
    align-items: flex-start;
    flex-direction: column;
  }
  .about-deck {
    font-size: 18px;
  }
  .about-chapter {
    padding-right: 32px;
    gap: 30px;
  }
  .about-invitation {
    gap: 35px;
  }
  .about-statement-bottom .eyebrow {
    display: none;
  }
}
@media (max-width: 700px) {
  .about-masthead {
    padding: 15px 20px;
    font-size: 8px;
  }
  .about-masthead > span:last-child {
    display: none;
  }
  .about-hero {
    grid-template-columns: 1fr;
    padding: 40px 24px 45px;
    gap: 38px;
  }
  .about-hero h1 {
    font-size: clamp(45px, 10vw, 68px);
  }
  .about-hero-note {
    margin-top: 24px;
  }
  .about-little-machine {
    width: min(100%, 390px);
    justify-self: center;
    transform: none;
    box-shadow: 5px 5px 0 var(--about-rule);
  }
  .about-machine-controls {
    flex-direction: row;
    align-items: center;
  }
  .about-chapter {
    grid-template-columns: 1fr;
    gap: 25px;
    padding: 45px 24px;
  }
  .about-margin-note {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
    font-size: 8px;
  }
  .about-margin-note > span:last-child {
    font-size: 9px;
  }
  .about-margin-note .roddy-logo {
    width: 50px;
  }
  .about-reading p {
    font-size: 16px;
    line-height: 1.85;
  }
  .about-reading h2 {
    font-size: 29px;
  }
  .about-statement {
    padding: 35px 24px 25px;
  }
  .about-statement h2 {
    font-size: clamp(26px, 6.2vw, 43px);
  }
  .about-statement-bottom {
    gap: 15px;
  }
  .about-statement-bottom p {
    font-size: 12px;
  }
  .about-beliefs {
    padding: 45px 24px;
  }
  .about-section-heading {
    flex-direction: column;
    gap: 15px;
  }
  .about-section-heading h2 {
    font-size: 30px;
  }
  .about-principles {
    grid-template-columns: 1fr;
  }
  .about-principle {
    border-right: 0;
    border-bottom: 1px solid var(--about-rule);
    padding: 25px;
  }
  .about-principle:last-child {
    border-bottom: 0;
  }
  .about-principle h3 {
    margin-top: 25px;
    max-width: 100%;
  }
  .about-principle p {
    font-size: 15px;
  }
  .about-invitation {
    grid-template-columns: 1fr;
    padding: 40px 24px;
    gap: 40px;
  }
  .about-repair-promise {
    margin: 0 24px 45px;
    padding: 24px;
    box-shadow: 5px 5px 0 var(--about-rule);
  }
  .about-promise-heading {
    align-items: flex-start;
  }
  .about-promise-heading .roddy-logo {
    width: 48px;
  }
  .about-promise-body {
    grid-template-columns: 1fr;
    gap: 15px;
  }
  .about-repair-promise h2 {
    font-size: clamp(24px, 5.6vw, 34px);
  }
  .about-invitation h2 {
    font-size: clamp(28px, 7.8vw, 44px);
  }
  .about-signoff {
    border-left: 0;
    border-top: 1px solid var(--about-rule);
    padding: 30px 0 0;
  }
  .about-signoff .roddy-logo {
    width: 175px;
  }
  .about-signoff > span {
    margin-top: 25px;
  }
  .about-signoff small {
    padding-top: 25px;
  }
}
</style>
