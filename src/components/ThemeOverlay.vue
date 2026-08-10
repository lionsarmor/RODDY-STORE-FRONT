<script setup>
import { useThemeStore } from "../stores/theme";
import { useUiStore } from "../stores/ui";

const theme = useThemeStore();
const ui = useUiStore();
</script>

<template>
  <div
    v-if="ui.themeOverlayOpen"
    class="fixed inset-0 z-100 flex items-center justify-center bg-black/55 p-6"
    @click.self="ui.closeThemeOverlay()"
  >
    <div class="max-h-[85vh] w-full max-w-xl overflow-y-auto border border-border bg-bg p-6">
      <div class="mb-4 flex items-center justify-between border-b border-border pb-3">
        <h3 class="font-mono text-sm uppercase tracking-wide">Select palette</h3>
        <button
          type="button"
          class="flex h-7 w-7 items-center justify-center border border-border font-mono hover:bg-accent hover:text-accent-text"
          @click="ui.closeThemeOverlay()"
        >
          ×
        </button>
      </div>

      <div v-for="(group, name) in theme.grouped" :key="name">
        <p class="mb-2 mt-5 font-mono text-[0.65rem] tracking-wider text-text-dim first:mt-0">{{ name }}</p>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <button
            v-for="t in group"
            :key="t.id"
            type="button"
            class="flex flex-col gap-2 border border-border bg-bg-alt p-3 text-left transition-colors"
            :class="t.id === theme.currentId ? 'ring-2 ring-inset ring-brand' : ''"
            @click="theme.apply(t.id)"
          >
            <span class="flex gap-1">
              <span v-for="(c, i) in t.swatch" :key="i" class="h-4 w-4 border border-black/25" :style="{ background: c }" />
            </span>
            <span class="font-mono text-xs uppercase tracking-wide">{{ t.label }}</span>
            <span class="font-mono text-[0.62rem] text-text-dim">{{ t.sub }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
