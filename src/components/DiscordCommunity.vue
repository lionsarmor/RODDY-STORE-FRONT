<script setup>
defineProps({compact:Boolean});
</script>
<template>
  <aside class="discord-community" :class="{compact}" aria-label="RODDY community">
    <div><h2>A little company, if you like.</h2><p>Follow the builds, share ideas, or ask a question in the RODDY Discord.</p></div>
    <a href="https://discord.gg/YVKJ5srkj" target="_blank" rel="noopener noreferrer" class="discord-join">Drop by Discord ↗</a>
  </aside>
</template>
<style scoped>
.discord-community{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:24px 0;border-bottom:1px solid var(--color-border);color:var(--color-text)}
.discord-community h2{font:600 16px/1.4 var(--font-sans);margin:0 0 6px}
.discord-community p{font:13px/1.65 var(--font-sans);max-width:60ch;color:var(--color-text-dim);margin:0}
.discord-join{flex-shrink:0;color:var(--color-text-dim);font:11px/1.5 var(--font-mono);text-decoration:underline;text-underline-offset:5px}
.discord-join:hover{color:var(--color-text)}
.discord-join:focus-visible{outline:2px solid var(--color-text);outline-offset:6px}
@media(max-width:650px){.discord-community{flex-direction:column;align-items:flex-start;gap:14px}}
</style>
