<script setup>
import { computed } from 'vue';
import { safeLink } from '../catalog-model.js';
const props = defineProps({ product: { type: Object, required: true } });
const editions = computed(() => Array.isArray(props.product.videoEditions) ? props.product.videoEditions : []);
const creditLink = computed(() => safeLink(props.product.projectCredit?.url));
</script>

<template>
  <section v-if="editions.length" class="video-editions" aria-labelledby="edition-heading">
    <div class="video-editions-heading">
      <p class="eyebrow">RODDY VIDEO / THE MULTI-EDITION MATINEE</p>
      <h2 id="edition-heading">ONE INVASION.<br>THREE WAYS TO WATCH.</h2>
      <p>Flying saucers. Questionable plans. A very good excuse to turn on an old computer.</p>
    </div>
    <div class="edition-grid">
      <article v-for="(edition, index) in editions" :key="edition.id" class="edition-card" :class="`edition-${edition.id}`">
        <div class="edition-screen" aria-hidden="true"><span>PLAN <b>9</b></span><small>{{ edition.screenLabel }}</small></div>
        <p class="eyebrow">0{{ index + 1 }} / {{ edition.format }}</p>
        <h3>{{ edition.name }}</h3>
        <p>{{ edition.description }}</p>
        <span class="edition-status">{{ edition.status }}</span>
      </article>
    </div>
    <aside v-if="product.projectCredit && creditLink" class="video-project-credit">
      <div>
        <p class="eyebrow">A ROUND OF APPLAUSE FOR THE PROJECTIONIST</p>
        <h3>{{ product.projectCredit.name }}</h3>
        <p>{{ product.projectCredit.description }}</p>
      </div>
      <a :href="creditLink" target="_blank" rel="noopener noreferrer" class="button">Meet X16 Media Studio ↗</a>
    </aside>
    <p class="edition-footnote">The original stays black and white. Phosphor is an optional alternate edition. The complete download bundle is coming soon.</p>
  </section>
</template>

<style scoped>
.video-editions{max-width:1280px;margin:0 auto;padding:clamp(24px,5vw,64px);border:1px solid var(--rule);background:var(--color-bg-alt)}
.video-editions-heading{max-width:720px;margin-bottom:32px}
.video-editions h2{font-size:clamp(28px,4.5vw,58px);line-height:1;letter-spacing:-.04em;margin:12px 0 20px;font-weight:900}
.video-editions p{line-height:1.6}
.edition-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}
.edition-card{min-width:0;border:1px solid var(--rule);padding:18px;background:var(--color-panel);display:flex;flex-direction:column;align-items:flex-start}
.edition-screen{width:100%;aspect-ratio:1.65;background:#151616;color:#f4eedf;border:7px solid #343532;border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;margin-bottom:22px;box-shadow:inset 0 0 30px #000}
.edition-screen span{font:700 clamp(24px,3vw,42px)/1 monospace;letter-spacing:-.08em}
.edition-screen b{font-size:1.5em}
.edition-screen small{font:10px/1.8 monospace;letter-spacing:.1em}
.edition-x16 .edition-screen{color:#b9bbff;background:repeating-linear-gradient(#171424 0 3px,#252039 3px 4px)}
.edition-phosphor .edition-screen{color:#9cf2a5;background:repeating-linear-gradient(#071b0b 0 3px,#132e18 3px 4px);text-shadow:0 0 10px #6fc583}
.edition-card h3{font-size:23px;font-weight:800;line-height:1.1;margin:10px 0}
.edition-card>p:not(.eyebrow){margin-bottom:22px;font-size:14px}
.edition-status{margin-top:auto;font:11px/1.5 var(--font-mono);text-transform:uppercase;border-top:1px solid var(--rule);padding-top:12px;width:100%}
.video-project-credit{display:flex;align-items:center;justify-content:space-between;gap:24px;margin-top:30px;padding-top:28px;border-top:2px solid var(--rule)}
.video-project-credit>div{max-width:650px}.video-project-credit h3{font-size:28px;font-weight:800;margin:8px 0}.video-project-credit .button{flex-shrink:0}
.edition-footnote{font-size:12px;margin:24px 0 0;color:var(--color-text-dim)}
@media(max-width:760px){.edition-grid{grid-template-columns:1fr}.edition-screen{max-width:320px}.video-project-credit{align-items:flex-start;flex-direction:column}.video-project-credit .button{white-space:normal}}
</style>
