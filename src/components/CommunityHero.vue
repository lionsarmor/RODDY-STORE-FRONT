<script setup>
defineProps({
  masthead: { type: String, required: true },
  edition: { type: String, required: true },
  kicker: { type: String, required: true },
  note: { type: String, default: '' },
});
</script>

<template>
  <div class="community-opening">
    <div class="community-masthead"><span>{{ masthead }}</span><span>{{ edition }}</span></div>
    <header class="community-hero">
      <div class="community-hero-copy">
        <p class="eyebrow"><span class="status-dot" aria-hidden="true" />{{ kicker }}</p>
        <h1><slot name="title" /></h1>
        <div class="community-deck"><slot name="description" /></div>
        <div class="community-hero-actions"><slot name="actions" /></div>
        <p v-if="note" class="community-hero-note">{{ note }}</p>
      </div>
      <div class="community-hero-art"><slot name="art" /></div>
    </header>
    <div class="spectrum-band" aria-hidden="true"><i v-for="n in 6" :key="n" /></div>
  </div>
</template>

<style scoped>
.community-masthead { display:flex; justify-content:space-between; gap:20px; padding:18px 32px; border-bottom:1px solid var(--rule); font:9px/1.6 var(--font-mono); letter-spacing:.08em; }
.community-hero { display:grid; grid-template-columns:1.35fr 1fr; align-items:center; gap:55px; padding:66px 32px 72px; }
.community-hero-copy,.community-hero-art { min-width:0; }
h1 { font:900 clamp(43px,6vw,78px)/1.02 var(--font-sans); letter-spacing:-.065em; margin:28px 0; }
h1 :deep(em) { font-style:normal; text-decoration:underline; text-decoration-color:var(--color-brand); text-decoration-thickness:5px; text-underline-offset:8px; }
.community-deck { max-width:39ch; font-size:20px; line-height:1.7; color:var(--color-text-dim); }
.community-hero-actions { display:flex; gap:20px; flex-wrap:wrap; align-items:center; margin-top:30px; }
.community-hero-note { margin-top:32px; max-width:55ch; color:var(--color-text-dim); font:9px/1.9 var(--font-mono); letter-spacing:.04em; }
@media(max-width:1050px) { .community-hero { gap:32px; } h1 { font-size:clamp(42px,5.7vw,64px); } .community-deck { font-size:18px; } }
@media(max-width:800px) { .community-masthead { padding:16px 24px; font-size:8px; } .community-masthead>span:last-child { display:none; } .community-hero { grid-template-columns:1fr; padding:42px 24px 50px; gap:38px; } h1 { font-size:clamp(37px,8.2vw,66px); } .community-hero-art { width:min(100%,460px); justify-self:center; } .community-hero-note { margin-top:24px; } }
@media(max-width:360px) { .community-hero { padding-inline:18px; } h1 { font-size:33px; } }
</style>
