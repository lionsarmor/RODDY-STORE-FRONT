<template>
  <div class="mx-auto max-w-6xl px-6 py-16">
    <div class="border border-dashed border-border p-12 text-center font-mono text-text-dim">
      <div class="relative mx-auto mb-8 h-[82px] w-[188px] overflow-hidden">
        <div
          class="boing-ball absolute left-0 top-0 h-12 w-12 rounded-full border-2 border-border"
          style="background-image: repeating-conic-gradient(#fff 0deg 45deg, var(--color-brand) 45deg 90deg); background-size: 100% 100%;"
        />
      </div>
      Page not found. <RouterLink to="/" class="text-brand">Back home →</RouterLink>
    </div>
  </div>
</template>
