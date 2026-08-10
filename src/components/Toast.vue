<script setup>
import { useUiStore } from "../stores/ui";
const ui = useUiStore();
</script>

<template>
  <div
    class="fixed bottom-6 left-1/2 z-200 -translate-x-1/2 border border-border bg-accent px-6 py-3 font-mono text-xs uppercase tracking-wide text-accent-text transition-all duration-200"
    :class="ui.toastVisible ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-2 opacity-0'"
  >
    {{ ui.toastMessage }}
  </div>
</template>
