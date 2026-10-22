<script setup>
defineProps({compact:Boolean});
</script>
<template>
  <aside class="discord-community" :class="{compact}">
    <div><span class="discord-eyebrow">THE RODDY DISCORD / COME HANG OUT</span><h2>{{compact?'Get in on the next thing.':'Good people. Weird computers. Big ideas.'}}</h2><p>Meet the maker, swap screenshots, follow the builds, and ask about alpha tester access. Bring your curiosity. Your retro obsession will fit right in.</p></div>
    <a href="https://discord.gg/YVKJ5srkj" target="_blank" rel="noopener noreferrer" class="discord-join">Join the Discord ↗</a>
  </aside>
</template>
<style scoped>
.discord-community{display:flex;align-items:center;justify-content:space-between;gap:32px;padding:36px;border-radius:18px;background:#17182b;color:#fff;border:1px solid #7277ff55}.discord-eyebrow{font:11px monospace;letter-spacing:.12em;color:#b7baff}.discord-community h2{font-size:clamp(22px,3vw,32px);line-height:1.1;font-weight:800;margin:12px 0}.discord-community p{font-size:14px;line-height:1.7;max-width:65ch;color:#d4d5e4}.discord-join{flex-shrink:0;background:#c1c3ff;color:#16172d;padding:15px 22px;border-radius:8px;font-weight:800;text-decoration:none}.discord-join:hover{background:#fff}.discord-join:focus-visible{outline:3px solid #fff;outline-offset:5px}.compact{padding:24px}.compact h2{font-size:24px}@media(max-width:650px){.discord-community{flex-direction:column;align-items:flex-start;padding:24px;gap:20px}}
</style>
