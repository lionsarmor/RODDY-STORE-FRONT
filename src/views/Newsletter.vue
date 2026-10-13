<script setup>
import { ref } from 'vue';
import NewsletterSignup from '../components/NewsletterSignup.vue';
import CommunityHero from '../components/CommunityHero.vue';
import RoddyLogo from '../components/RoddyLogo.vue';
import { SUPPORT_EMAIL } from '../forum-api.js';

const signupHeading = ref(null);
function jumpToSignup() {
  signupHeading.value?.scrollIntoView({block: 'start'});
  signupHeading.value?.focus({preventScroll: true});
}
const dispatches = [
  {number: '01', title: 'Fresh from the workbench.', text: 'Little experiments, new builds, and a look at what we’re making next.'},
  {number: '02', title: 'Something new to explore.', text: 'Games, hardware and software releases from our corner of the RODDY world.'},
  {number: '03', title: 'An occasional shop special.', text: 'Product news, advertising and offers. A little of the practical stuff, too.'},
];
</script>

<template>
  <article class="newsletter-world">
    <CommunityHero masthead="RODDY / POSTCARDS FROM THE WORKBENCH" edition="LOW FREQUENCY. HIGH CURIOSITY." kicker="A LITTLE SIGNAL. VERY OCCASIONALLY." note="NEW BUILDS. NEW RELEASES. OCCASIONAL ADS AND OFFERS. ONLY WHEN WE HAVE SOMETHING TO SHARE.">
      <template #title>LESS SCROLL.<br /><em>MORE SIGNAL.</em></template>
      <template #description>A small postcard from our corner of the future. For the builders, the daydreamers, and the people who keep asking “what if?”</template>
      <template #actions><button class="button primary" @click="jumpToSignup">Tune me in ↓</button><RouterLink to="/contact" class="text-button">Back to the community ↗</RouterLink></template>
      <template #art>
        <div class="newsletter-postcard">
          <div class="postcard-heading"><RoddyLogo kind="full_logo" /><span>OCCASIONAL<br />DISPATCHES</span></div>
          <div class="postcard-art" aria-hidden="true">
            <span class="postcard-orbit postcard-orbit-one" /><span class="postcard-orbit postcard-orbit-two" />
            <svg viewBox="0 0 160 112" class="postcard-envelope" fill="none"><path d="M13 18h134v78H13z" fill="var(--color-panel)" stroke="currentColor" stroke-width="3"/><path d="m14 20 66 46 66-46M14 94l44-44m88 44-44-44" stroke="currentColor" stroke-width="3"/><path d="M63 11h34M80 0v24" stroke="var(--color-brand)" stroke-width="4"/></svg>
            <span class="postcard-star">✳</span>
          </div>
          <div class="postcard-message"><p>A LITTLE<br /><em>SIGNAL.</em></p><span>FROM OUR WORKBENCH.<br />TO YOUR WORLD.</span></div>
          <div class="postcard-footer"><span>NO NEED TO KEEP UP.</span><span>JUST KEEP WONDERING.</span></div>
        </div>
      </template>
    </CommunityHero>

    <section class="newsletter-dispatches" aria-labelledby="dispatches-heading">
      <div class="newsletter-section-heading"><p class="eyebrow">01 / WHAT’S ON THE WAVELENGTH</p><h2 id="dispatches-heading">A few things<br />worth opening.</h2></div>
      <div class="newsletter-dispatch-grid">
        <section v-for="dispatch in dispatches" :key="dispatch.number" class="newsletter-dispatch">
          <span class="dispatch-number">{{dispatch.number}}<span aria-hidden="true">↗</span></span>
          <h3>{{dispatch.title}}</h3><p>{{dispatch.text}}</p>
        </section>
      </div>
    </section>

    <section class="newsletter-subscribe" aria-labelledby="signup-heading">
      <div class="newsletter-subscribe-copy"><p class="eyebrow">02 / KEEP IN TOUCH</p><h2>A little curiosity.<br /><em>Delivered.</em></h2><p>We spend most of our time making things. When there’s something to share, we’ll send a little signal your way.</p><p>You’ll get updates, releases and occasional offers. Leave whenever you like by replying “unsubscribe” to any newsletter.</p><div class="newsletter-frequency"><span aria-hidden="true">↗</span><span>YOUR ATTENTION IS YOURS.<br />THANKS FOR SHARING A LITTLE OF IT.</span></div></div>
      <div class="newsletter-subscribe-card"><div class="subscribe-card-heading"><span class="eyebrow">POSTCARDS FROM RODDY</span><RoddyLogo kind="badge" /></div><h2 id="signup-heading" ref="signupHeading" tabindex="-1">Leave an address.<br />Keep a little signal.</h2><NewsletterSignup variant="editorial" /><p class="newsletter-privacy">Your email stays on our private server, never in the public catalog.</p></div>
    </section>

    <section class="newsletter-leave" aria-labelledby="newsletter-leave-heading">
      <div class="newsletter-leave-note"><p class="eyebrow">03 / ALWAYS YOUR CHOICE</p><span>NO HARD FEELINGS.<br />REALLY.</span></div>
      <div><h2 id="newsletter-leave-heading">Want to leave the list?</h2><p>Reply “unsubscribe” to a newsletter, or <a :href="`mailto:${SUPPORT_EMAIL}?subject=Unsubscribe%20from%20RODDY`">email RODDY to unsubscribe</a> from the address you signed up with. We handle requests manually before the next mailing.</p><p>Already unsubscribed? Signing up here will keep that choice. <RouterLink to="/contact">Contact us</RouterLink> if you have questions about your subscription.</p></div>
    </section>
  </article>
</template>

<style scoped>
.newsletter-world {max-width:1280px;margin-inline:auto;overflow-wrap:anywhere;}
.newsletter-postcard {border:1px solid var(--color-text);padding:22px;background:var(--color-panel);box-shadow:8px 8px 0 var(--rule);transform:rotate(-2deg);}
.postcard-heading {display:flex;align-items:center;justify-content:space-between;gap:24px;}
.postcard-heading .roddy-logo {width:min(48%,170px);height:auto;}
.postcard-heading>span {font:8px/1.8 var(--font-mono);letter-spacing:.06em;text-align:right;}
.postcard-art {position:relative;isolation:isolate;overflow:hidden;border-block:1px solid var(--rule);margin:22px 0;padding:26px 0;background:var(--color-bg);min-height:180px;display:grid;place-items:center;}
.postcard-envelope {width:170px;height:auto;position:relative;z-index:1;transform:rotate(-8deg);}
.postcard-orbit {position:absolute;border:1px solid var(--color-text);border-radius:50%;width:300px;height:120px;transform:rotate(-22deg);opacity:.25;}
.postcard-orbit-two {width:340px;height:170px;transform:rotate(22deg);}
.postcard-star {position:absolute;right:24px;top:18px;color:var(--color-brand);font:46px/1 var(--font-sans);}
.postcard-message {display:flex;justify-content:space-between;align-items:end;gap:20px;}
.postcard-message>p {font:850 44px/1.02 var(--font-sans);letter-spacing:-.055em;}
.postcard-message em {font-style:normal;color:var(--color-brand);}
.postcard-message>span {font:8px/1.9 var(--font-mono);text-align:right;max-width:20ch;}
.postcard-footer {display:flex;justify-content:space-between;gap:16px;border-top:1px solid var(--rule);padding-top:16px;margin-top:22px;font:7px/1.8 var(--font-mono);letter-spacing:.04em;}
.newsletter-dispatches {padding:65px 32px;}
.newsletter-section-heading {display:flex;align-items:baseline;justify-content:space-between;gap:24px;margin-bottom:32px;}
.newsletter-section-heading h2 {font:750 33px/1.12 var(--font-sans);letter-spacing:-.045em;}
.newsletter-dispatch-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border:1px solid var(--rule);}
.newsletter-dispatch {padding:28px 25px;background:var(--color-panel);border-right:1px solid var(--rule);}
.newsletter-dispatch:last-child {border-right:0;}
.dispatch-number {display:flex;justify-content:space-between;font:25px var(--font-mono);color:var(--color-text-dim);}
.dispatch-number>span {color:var(--color-brand);}
.newsletter-dispatch h3 {font:750 25px/1.2 var(--font-sans);letter-spacing:-.04em;margin:35px 0 18px;max-width:15ch;}
.newsletter-dispatch p {font-size:14px;line-height:1.9;color:var(--color-text-dim);}
.newsletter-subscribe {display:grid;grid-template-columns:1fr 1fr;align-items:center;gap:70px;padding:60px 45px;background:var(--color-bg-alt);border-block:1px solid var(--rule);}
.newsletter-subscribe-copy h2 {font:850 clamp(34px,4vw,52px)/1.08 var(--font-sans);letter-spacing:-.055em;margin:26px 0;}
.newsletter-subscribe-copy h2 em {font-style:normal;text-decoration:underline;text-decoration-color:var(--color-brand);text-decoration-thickness:3px;text-underline-offset:5px;}
.newsletter-subscribe-copy>p:not(.eyebrow) {font-size:16px;line-height:1.9;color:var(--color-text-dim);margin-bottom:20px;max-width:42ch;}
.newsletter-frequency {display:flex;align-items:center;gap:20px;border-top:1px solid var(--rule);padding-top:23px;margin-top:32px;}
.newsletter-frequency>span:first-child {font:38px/1 var(--font-sans);color:var(--color-brand);}
.newsletter-frequency>span:last-child {font:8px/1.9 var(--font-mono);letter-spacing:.04em;}
.newsletter-subscribe-card {padding:30px;border:1px solid var(--color-text);background:var(--color-panel);box-shadow:6px 6px 0 var(--rule);min-width:0;}
.subscribe-card-heading {display:flex;justify-content:space-between;align-items:center;gap:20px;}
.subscribe-card-heading .eyebrow {font-size:8px;}
.subscribe-card-heading .roddy-logo {width:58px;height:auto;}
.newsletter-subscribe-card h2 {font:750 30px/1.15 var(--font-sans);letter-spacing:-.04em;margin:25px 0;scroll-margin-top:180px;}
.newsletter-privacy {font:9px/1.9 var(--font-mono);color:var(--color-text-dim);padding-top:20px;margin-top:22px;border-top:1px solid var(--rule);}
.newsletter-leave {display:grid;grid-template-columns:1fr 3fr;gap:45px;padding:65px 32px;}
.newsletter-leave-note>span {display:block;font:12px/1.8 var(--font-mono);margin-top:26px;}
.newsletter-leave h2 {font:750 30px/1.2 var(--font-sans);letter-spacing:-.04em;margin-bottom:22px;}
.newsletter-leave p:not(.eyebrow) {font-size:14px;line-height:1.9;color:var(--color-text-dim);margin-bottom:16px;max-width:67ch;}
.newsletter-leave a {color:var(--color-text);text-decoration:underline;text-underline-offset:4px;}
@media(max-width:1050px){.newsletter-subscribe{gap:35px;padding-inline:32px;}.newsletter-dispatch{padding:24px 20px;}.newsletter-dispatch h3{font-size:23px;}.newsletter-leave{gap:30px;}}
@media(max-width:800px){.newsletter-postcard{transform:none;box-shadow:5px 5px 0 var(--rule);}.newsletter-dispatches{padding:42px 24px;}.newsletter-section-heading{align-items:flex-start;flex-direction:column;}.newsletter-subscribe{grid-template-columns:1fr;padding:42px 24px;gap:30px;}.newsletter-subscribe-card{width:100%;max-width:560px;}.newsletter-leave{grid-template-columns:1fr;padding:42px 24px;gap:24px;}.newsletter-leave-note>span{margin-top:15px;}}
@media(max-width:600px){.newsletter-dispatch-grid{grid-template-columns:1fr;}.newsletter-dispatch{border-right:0;border-bottom:1px solid var(--rule);}.newsletter-dispatch:last-child{border-bottom:0;}.newsletter-dispatch h3{max-width:none;margin-top:22px;}.newsletter-subscribe-card{padding:24px 20px;}.newsletter-subscribe-card h2{font-size:27px;}.postcard-message>p{font-size:40px;}}
@media(max-width:360px){.newsletter-postcard{padding:18px;}.postcard-message{gap:12px;}.postcard-message>p{font-size:34px;}.postcard-message>span{font-size:7px;}.postcard-footer{font-size:6px;}}
</style>
