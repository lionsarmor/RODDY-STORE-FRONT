<script setup>
import NewsletterSignup from '../components/NewsletterSignup.vue';
</script>
<template>
  <section class="mx-auto max-w-xl px-6 py-16">
    <p class="font-mono text-sm text-text-dim">POSTCARDS FROM RODDY</p>
    <h1 class="my-5 text-4xl font-bold">A little signal in your inbox.</h1>
    <p class="mb-6">New builds, releases, occasional ads and offers. Only when we have something to share.</p>
    <div class="newsletter-card"><NewsletterSignup /></div>
    <h2 class="mb-3 mt-10 text-xl font-bold">Want to leave the list?</h2>
    <p>Reply “unsubscribe” to a newsletter, or <a class="underline" href="mailto:roddy2020@protonmail.com?subject=Unsubscribe%20from%20RODDY">email RODDY to unsubscribe</a> from the address you signed up with. We handle requests manually before the next mailing. We keep your email on our private server, never in the public catalog.</p>
    <p class="mt-4 text-sm text-text-dim">Already unsubscribed? Signing up here will keep that choice. Contact us if you have questions about your subscription.</p>
  </section>
</template>
<style scoped>.newsletter-card{padding:25px;background:#fff8e9;color:#182023;border-radius:16px;border-top:8px solid #e96b8a}</style>
