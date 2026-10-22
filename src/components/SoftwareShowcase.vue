<script setup>
import {computed,ref} from 'vue';
import {productImageUrl} from '../stores/catalog.js';
import FreeDownload from './FreeDownload.vue';
import DiscordCommunity from './DiscordCommunity.vue';
const props=defineProps({product:Object});
const orbit=computed(()=>props.product.id==='orbit');
const lightbox=ref(null),selected=ref(null);
function enlarge(src,caption){selected.value={src,caption};lightbox.value.showModal();}
function editions(){document.getElementById('software-editions')?.scrollIntoView({behavior:'smooth'});}
</script>
<template>
  <article class="software-launch" :class="{'software-orbit':orbit,'orbit-centered':orbit,'buddy-centered':!orbit}">
    <nav class="software-nav" aria-label="Breadcrumb"><RouterLink to="/shop">← Back to the store</RouterLink><span>RODDY SOFTWARE LAB / {{orbit?'002':'001'}}</span></nav>
    <section class="software-hero">
      <div class="software-intro"><p class="lab-label"><span /> ALPHA · INVITED TESTERS ONLY</p><h1>{{product.name}}<span aria-hidden="true">{{orbit?'◌':'_'}}</span></h1><h2>{{product.launchHeadline}}</h2><p class="hero-description">{{product.description}}</p><div class="software-actions"><button class="lab-button" @click="editions">{{orbit?'Get your alpha build':'Pick your machine'}} ↓</button><a href="https://discord.gg/YVKJ5srkj" target="_blank" rel="noopener noreferrer">Find your people on Discord ↗</a></div><p class="tiny-print">$0 tester downloads · Email + beta tester code required</p></div>
      <div class="hero-screen"><div class="screen-chrome"><span>● ● ●</span><span>{{orbit?'YOUR LITTLE UNIVERSE':'FRIENDS. MESSAGES. CLASSIC.'}}</span><span>↗</span></div><button @click="enlarge(product.images[0],product.name+' alpha preview')" :aria-label="'Enlarge '+product.name+' alpha preview'"><img :src="productImageUrl(product.images[0])" :alt="product.name+' running in a demonstration session'" /></button><div class="screen-caption"><span>ACTUAL DEVELOPMENT BUILD</span><span>{{orbit?'CAPTURED FRESH FOR THIS PAGE':'RETRO CLIENT / DEMONSTRATION DATA'}}</span></div></div>
    </section>
    <div class="software-ticker" aria-hidden="true"><span v-for="n in 3" :key="n">{{orbit?'YOUR PEOPLE ✦ YOUR SPACE ✦ TOGETHER, FOR NOW':'SIGN ON ✦ SAY HEY ✦ STAY A LITTLE LONGER'}} ✦ </span></div>
    <section class="software-story"><p class="lab-label">{{orbit?'MAKE ROOM FOR SOMETHING GOOD':'THE GOOD OLD DAYS HAVE A NEW MESSAGE'}}</p><h2>{{product.launchSubheading}}</h2><div class="feature-row"><div v-for="(feature,i) in product.softwareFeatures" :key="feature.title"><span>0{{i+1}} /</span><h3>{{feature.title}}</h3><p>{{feature.text}}</p></div></div></section>
    <section class="software-editions" id="software-editions" aria-labelledby="software-editions-title"><div class="edition-heading"><div><p class="lab-label">{{orbit?'ONE APP. THREE PERSONALITIES.':'SEVEN MACHINES. SEVEN LITTLE PERSONALITIES.'}}</p><h2 id="software-editions-title">{{orbit?'Your next hangout starts here.':'Which BUDDY are you?'}}</h2></div><span class="alpha-stamp">ALPHA<br>TEST CREW</span></div><p class="section-intro">{{product.editionIntro}}</p>
      <div class="software-edition-grid" :class="{'single-edition':orbit}"><article v-for="(edition,i) in product.softwareEditions" :key="edition.id" class="software-edition" :style="{'--edition-color':edition.color}"><div class="edition-label"><span>EDITION / {{String(i+1).padStart(2,'0')}}</span><span>ALPHA</span></div><button class="edition-image" @click="enlarge(edition.image,edition.name+' alpha screenshot')" :aria-label="'Enlarge '+edition.name+' screenshot'"><img :src="productImageUrl(edition.image)" :alt="edition.name+' alpha demonstration'" loading="lazy" /><span>TAKE A CLOSER LOOK ⤢</span></button><div class="edition-copy"><p class="edition-tagline">{{edition.tagline}}</p><h3>{{edition.name}}</h3><p>{{edition.description}}</p><details v-if="!orbit" class="edition-setup"><summary>Setup &amp; compatibility</summary><p>{{edition.requirements}}</p></details><p v-else class="edition-requirement">{{edition.requirements}}</p><div v-if="edition.secondImage" class="edition-extra"><button @click="enlarge(edition.secondImage,edition.name+' alternate view')">Another look ⤢</button></div><FreeDownload v-if="edition.downloadable" :product="product" :edition-id="edition.id" :label="edition.name" button-class="lab-button edition-download">Unlock this alpha ↓</FreeDownload><p v-else class="edition-requirement">Package in preparation. Follow progress on Discord.</p></div></article></div>
      <div class="alpha-notice"><strong>Fresh from the workbench.</strong><p>{{product.releaseNote}} Tester codes unlock these downloads; they are separate from any in-app account or lounge invitation.</p><a href="https://discord.gg/YVKJ5srkj" target="_blank" rel="noopener noreferrer">Need a tester code? Ask in the RODDY Discord ↗</a></div>
    </section>
    <section class="software-screens" aria-labelledby="screens-heading"><p class="lab-label">{{orbit?'FRESH CAPTURES / REAL INTERFACE':'THE PIXELS SPEAK FOR THEMSELVES'}}</p><h2 id="screens-heading">{{orbit?'Same universe. Different moods.':'Old-school looks. New conversations.'}}</h2><p class="section-intro">{{orbit?'ORBIT, BUDDY and RODDY skins, chess, a shared whiteboard, lounge design, and a phone-sized peek. These are new browser captures of the working alpha, with demonstration data.':'Real development screenshots from the different clients. Demo contacts and conversations show the interface; emulator previews do not imply verified physical-hardware support.'}}</p><div class="software-screen-grid"><figure v-for="shot in product.softwareScreenshots" :key="shot.image"><button @click="enlarge(shot.image,shot.caption)" :aria-label="'Enlarge: '+shot.caption"><img :src="productImageUrl(shot.image)" :alt="shot.caption" loading="lazy" /></button><figcaption>{{shot.caption}} <span>⤢</span></figcaption></figure></div></section>
    <DiscordCommunity compact />
    <div class="software-next"><span>MORE FROM THE RODDY LAB</span><RouterLink :to="'/product/'+(orbit?'buddy':'orbit')">{{orbit?'Meet BUDDY. Your old computer misses you.':'Meet ORBIT. Your people, in a new universe.'}} ↗</RouterLink></div>
    <dialog ref="lightbox" class="software-lightbox" aria-label="Software screenshot"><button class="lightbox-close" @click="lightbox.close()" aria-label="Close screenshot">Close ×</button><template v-if="selected"><img :src="productImageUrl(selected.src)" :alt="selected.caption" /><p>{{selected.caption}}</p></template></dialog>
  </article>
</template>
<style scoped>
.software-launch{--lab-accent:#124ee8;--lab-paper:#f4f1e9;--lab-ink:#152337;--lab-line:#15233730;background:var(--lab-paper);color:var(--lab-ink);padding:0 36px 36px;max-width:1320px;margin:0 auto 60px;border-radius:0 0 24px 24px}.software-launch.software-orbit{--lab-accent:#edbe88;--lab-paper:#11171e;--lab-ink:#f3eee6;--lab-line:#f3eee62b}.software-nav{display:flex;justify-content:space-between;gap:16px;padding:24px 0;border-bottom:1px solid var(--lab-line);font:11px monospace;letter-spacing:.05em}.software-nav a:hover{text-decoration:underline}.software-hero{display:grid;grid-template-columns:.85fr 1.15fr;align-items:center;gap:34px;padding:60px 0 56px}.lab-label{font:11px monospace;letter-spacing:.1em;line-height:1.7;color:var(--lab-accent)}.lab-label>span{display:inline-block;width:7px;height:7px;margin-right:7px;border-radius:50%;background:var(--lab-accent)}.software-intro h1{font-size:clamp(65px,8vw,108px);font-weight:900;line-height:1;letter-spacing:-.07em;margin:20px 0}.software-intro h1>span{color:var(--lab-accent)}.software-intro h2{font-size:clamp(25px,3vw,36px);font-weight:800;letter-spacing:-.035em;line-height:1.08;max-width:15ch}.hero-description{margin:20px 0 26px;line-height:1.75;font-size:15px;max-width:47ch;opacity:.8}.software-actions{display:flex;gap:18px;align-items:center;flex-wrap:wrap}.software-actions a{font-size:12px;text-decoration:underline;text-underline-offset:4px}.lab-button{display:inline-flex;justify-content:center;align-items:center;background:var(--lab-accent);color:var(--lab-paper);border:0;border-radius:7px;padding:14px 18px;font-size:13px;font-weight:800;cursor:pointer}.lab-button:hover{filter:brightness(1.13)}button:focus-visible,a:focus-visible{outline:3px solid var(--lab-accent);outline-offset:4px}.tiny-print{font:10px monospace;margin-top:20px;opacity:.65}.hero-screen{border:1px solid var(--lab-line);border-radius:12px;overflow:hidden;background:#10151c;box-shadow:10px 14px 0 var(--lab-line);transform:rotate(-2deg)}.software-orbit .hero-screen{transform:rotate(1deg)}.screen-chrome,.screen-caption{display:flex;justify-content:space-between;gap:12px;font:9px monospace;letter-spacing:.06em;background:#172332;color:#cdd8e5;padding:12px}.screen-chrome>span:first-child{color:#e6b967;letter-spacing:4px}.hero-screen button{display:block;width:100%;cursor:zoom-in}.hero-screen img{width:100%;display:block;object-fit:contain;max-height:490px}.screen-caption{font-size:8px;background:#0b121a}.software-ticker{display:flex;overflow:hidden;white-space:nowrap;gap:12px;background:var(--lab-accent);color:var(--lab-paper);padding:13px 18px;font:12px monospace;letter-spacing:.08em;margin:0 -36px}.software-story,.software-editions,.software-screens{padding:60px 0;border-bottom:1px solid var(--lab-line)}.software-story>h2,.edition-heading h2,.software-screens>h2{font-size:clamp(30px,4vw,48px);font-weight:850;letter-spacing:-.045em;line-height:1.1;margin:14px 0 28px;max-width:24ch}.feature-row{display:grid;grid-template-columns:repeat(3,1fr);gap:30px}.feature-row>div>span{font:11px monospace;color:var(--lab-accent)}.feature-row h3{font-size:19px;font-weight:800;margin:14px 0 9px}.feature-row p,.section-intro{font-size:14px;line-height:1.8;opacity:.75}.edition-heading{display:flex;justify-content:space-between;gap:20px;align-items:center}.alpha-stamp{border:2px solid var(--lab-accent);color:var(--lab-accent);font:800 14px monospace;padding:14px;transform:rotate(8deg);line-height:1.4}.section-intro{max-width:75ch;margin-bottom:30px}.software-edition-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.software-edition{border:1px solid var(--lab-line);border-top:5px solid var(--edition-color);border-radius:10px;overflow:hidden;background:#ffffff60;display:flex;flex-direction:column}.software-orbit .software-edition{background:#ffffff05}.edition-label{display:flex;justify-content:space-between;padding:13px 18px;font:10px monospace;letter-spacing:.08em;border-bottom:1px solid var(--lab-line)}.edition-label>span:last-child{color:var(--edition-color);font-weight:bold}.edition-image{display:flex;align-items:center;justify-content:center;position:relative;background:#10151c;padding:24px;width:100%;height:330px;cursor:zoom-in}.edition-image img{max-width:100%;max-height:100%;object-fit:contain;image-rendering:pixelated}.software-orbit .edition-image img{image-rendering:auto}.edition-image>span{position:absolute;bottom:8px;right:10px;font:8px monospace;color:#cdd8e5;background:#0b121ac9;padding:5px}.edition-copy{display:flex;flex-direction:column;align-items:flex-start;padding:24px;flex:1}.edition-tagline{font:10px monospace;text-transform:uppercase;letter-spacing:.08em;color:var(--edition-color)}.edition-copy h3{font-size:29px;line-height:1.1;font-weight:850;letter-spacing:-.04em;margin:12px 0}.edition-copy>p:not(.edition-tagline){font-size:14px;line-height:1.7;opacity:.8}.edition-copy .edition-requirement{font-size:11px!important;opacity:.65!important;margin:16px 0}.edition-extra{margin:0 0 20px;font:11px monospace;text-decoration:underline}:deep(.edition-download){margin-top:auto;display:inline-flex;justify-content:center;align-items:center;background:var(--edition-color);color:#fff;border:0;border-radius:7px;padding:14px 18px;font-size:13px;font-weight:800;cursor:pointer}.single-edition .software-edition{grid-column:1/-1;display:grid;grid-template-columns:1.2fr 1fr}.single-edition .edition-label{grid-column:1/-1}.single-edition .edition-image{height:100%;min-height:320px}.single-edition :deep(.edition-download){color:#171b24}.alpha-notice{display:grid;gap:9px;border-left:3px solid var(--lab-accent);padding:18px 24px;margin-top:30px;background:var(--lab-line);font-size:13px;line-height:1.7}.alpha-notice a{text-decoration:underline;text-underline-offset:4px;font-weight:700}.software-screen-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.software-screen-grid figure{border:1px solid var(--lab-line);border-radius:9px;overflow:hidden;display:flex;flex-direction:column}.software-screen-grid figure>button{width:100%;height:330px;padding:18px;background:#10151c;cursor:zoom-in;flex:none}.software-screen-grid img{width:100%;height:100%;max-height:360px;object-fit:contain}.software-screen-grid figcaption{display:flex;justify-content:space-between;padding:14px;font:11px monospace;line-height:1.6}.software-screens{border-bottom:0}.software-next{display:grid;gap:12px;margin:36px 0 0;padding:24px 0;border-top:1px solid var(--lab-line)}.software-next>span{font:10px monospace;letter-spacing:.1em;opacity:.6}.software-next>a{font-size:22px;font-weight:800}.software-lightbox{max-width:calc(100vw - 24px);max-height:calc(100dvh - 24px);margin:auto;border:1px solid #ffffff44;border-radius:10px;background:#10151c;color:#fff;padding:20px;overflow:auto}.software-lightbox::backdrop{background:#000d;backdrop-filter:blur(5px)}.software-lightbox img{max-height:80dvh;max-width:100%;object-fit:contain;display:block;margin:auto}.software-lightbox p{font:12px monospace;margin:15px 0}.lightbox-close{display:block;margin:0 0 14px auto;padding:8px 12px;border:1px solid #ffffff66;border-radius:5px;font-size:13px}@media(max-width:850px){.software-hero{grid-template-columns:1fr;gap:36px;padding:40px 0}.software-intro h2{max-width:24ch}.hero-description{max-width:60ch}.hero-screen{max-width:650px}.feature-row{gap:20px}.edition-image{height:260px}.single-edition .software-edition{display:flex}.single-edition .edition-image{min-height:0;height:300px}.software-screen-grid figure>button{height:250px}}@media(max-width:580px){.software-launch{padding:0 20px 24px;border-radius:0}.software-nav{font-size:9px}.software-nav>span{max-width:16ch;text-align:right}.software-ticker{margin:0 -20px}.software-story,.software-editions,.software-screens{padding:40px 0}.feature-row,.software-edition-grid,.software-screen-grid{grid-template-columns:1fr}.feature-row{gap:24px}.feature-row h3{margin:8px 0}.alpha-stamp{font-size:10px;padding:10px}.edition-heading h2{font-size:31px}.edition-image{height:290px}.software-screen-grid figure>button{height:auto;min-height:240px}.software-screen-grid img{max-height:330px}.screen-caption{font-size:7px}.software-next>a{font-size:19px}}
/* A smaller, centered BUDDY feature, with the shop's framed product feel. */
.software-launch.buddy-centered {
  width: calc(100% - 48px);
  max-width: 1040px;
  margin: 24px auto 48px;
  padding: 0 28px 24px;
  border: 1px solid var(--lab-line);
  border-radius: 12px;
}
.buddy-centered .software-nav { padding: 16px 0; font-size: 10px; }
.buddy-centered .software-hero { grid-template-columns: 1fr 1fr; gap: 32px; padding: 32px 0; }
.buddy-centered .software-intro h1 { font-size: clamp(48px, 5.8vw, 72px); margin: 14px 0; }
.buddy-centered .software-intro h2 { font-size: clamp(22px, 2.6vw, 28px); max-width: 21ch; }
.buddy-centered .hero-description { font-size: 13px; line-height: 1.7; margin: 16px 0 20px; }
.buddy-centered .software-actions { gap: 14px; }
.buddy-centered .software-actions a { font-size: 11px; }
.buddy-centered .lab-button { padding: 11px 14px; font-size: 12px; }
.buddy-centered .tiny-print { font-size: 9px; line-height: 1.6; margin-top: 14px; }
.buddy-centered .hero-screen { max-width: 330px; margin: 0 auto; transform: rotate(1deg); box-shadow: 6px 8px 0 var(--lab-line); }
.buddy-centered .hero-screen img { max-height: 300px; }
.buddy-centered .screen-chrome { font-size: 8px; padding: 9px; }
.buddy-centered .screen-caption { font-size: 7px; padding: 9px; }
.buddy-centered .software-ticker { margin: 0 -28px; padding: 10px 18px; font-size: 10px; }
.buddy-centered .software-story,
.buddy-centered .software-editions,
.buddy-centered .software-screens { padding: 32px 0; }
.buddy-centered .software-story > h2,
.buddy-centered .edition-heading h2,
.buddy-centered .software-screens > h2 { font-size: clamp(24px, 3vw, 30px); margin: 10px 0 20px; max-width: 29ch; }
.buddy-centered .lab-label { font-size: 10px; }
.buddy-centered .feature-row { gap: 24px; }
.buddy-centered .feature-row h3 { font-size: 16px; margin: 9px 0 7px; }
.buddy-centered .feature-row p,
.buddy-centered .section-intro { font-size: 12px; line-height: 1.7; }
.buddy-centered .section-intro { margin-bottom: 20px; max-width: 85ch; }
.buddy-centered .alpha-stamp { font-size: 11px; padding: 10px; }
.buddy-centered .software-edition-grid { gap: 16px; }
.buddy-centered .software-edition { display: grid; grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr); border-top-width: 3px; border-radius: 7px; }
.buddy-centered .edition-label { grid-column: 1 / -1; padding: 10px 12px; font-size: 9px; }
.buddy-centered .edition-image { height: 100%; min-height: 175px; padding: 12px; }
.buddy-centered .edition-image > span { font-size: 6px; right: 5px; bottom: 5px; padding: 4px; }
.buddy-centered .edition-copy { min-width: 0; padding: 16px; }
.buddy-centered .edition-tagline { font-size: 8px; line-height: 1.6; }
.buddy-centered .edition-copy h3 { font-size: 21px; margin: 8px 0 10px; }
.buddy-centered .edition-copy > p:not(.edition-tagline) { font-size: 12px; line-height: 1.6; }
.edition-setup { margin: 12px 0; font-size: 10px; line-height: 1.7; }
.edition-setup summary { cursor: pointer; font-weight: 700; }
.edition-setup p { margin-top: 8px; opacity: .8; }
.buddy-centered .edition-extra { font-size: 10px; margin-bottom: 14px; }
.buddy-centered :deep(.edition-download) { padding: 10px 12px; font-size: 11px; border-radius: 5px; }
.buddy-centered .software-edition:last-child:nth-child(odd) { grid-column: 1 / -1; width: calc(50% - 8px); justify-self: center; }
.buddy-centered .alpha-notice { margin-top: 22px; padding: 14px 18px; font-size: 11px; }
.buddy-centered .software-screen-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.buddy-centered .software-screen-grid figure > button { height: 165px; padding: 10px; }
.buddy-centered .software-screen-grid figcaption { padding: 10px; font-size: 9px; }
.buddy-centered .software-next { margin-top: 24px; padding: 20px 0 0; }
.buddy-centered .software-next > a { font-size: 18px; }
@media (max-width: 850px) {
  .buddy-centered .software-hero { gap: 24px; }
  .buddy-centered .software-intro h1 { font-size: 58px; }
  .buddy-centered .software-edition { display: flex; }
  .buddy-centered .edition-image { height: 175px; min-height: 0; }
  .buddy-centered .edition-copy { padding: 16px; }
  .buddy-centered .software-screen-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 580px) {
  .software-launch.buddy-centered { width: calc(100% - 24px); padding: 0 16px 20px; margin-top: 12px; }
  .buddy-centered .software-nav { font-size: 9px; gap: 10px; }
  .buddy-centered .software-hero { grid-template-columns: 1fr; gap: 22px; padding: 24px 0; }
  .buddy-centered .software-intro h1 { font-size: 54px; }
  .buddy-centered .software-intro h2 { font-size: 24px; }
  .buddy-centered .hero-screen { max-width: 275px; }
  .buddy-centered .software-ticker { margin: 0 -16px; }
  .buddy-centered .software-story,
  .buddy-centered .software-editions,
  .buddy-centered .software-screens { padding: 26px 0; }
  .buddy-centered .feature-row { gap: 18px; }
  .buddy-centered .software-edition:last-child:nth-child(odd) { width: 100%; }
  .buddy-centered .edition-copy h3 { font-size: 22px; }
  .buddy-centered .edition-image { height: 180px; }
  .buddy-centered .software-screen-grid figure > button { min-height: 0; height: 130px; padding: 8px; }
  .buddy-centered .software-screen-grid figcaption { font-size: 8px; }
}

/* ORBIT shares the centered feature frame, with room for its wide screenshots. */
.software-launch.orbit-centered {
  width: calc(100% - 48px);
  max-width: 1040px;
  margin: 24px auto 48px;
  padding: 0 28px 24px;
  border: 1px solid var(--lab-line);
  border-radius: 12px;
}
.orbit-centered .software-nav { padding: 16px 0; font-size: 10px; }
.orbit-centered .software-hero { grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr); gap: 28px; padding: 32px 0; }
.orbit-centered .software-intro h1 { font-size: clamp(48px, 5.8vw, 72px); margin: 14px 0; }
.orbit-centered .software-intro h2 { font-size: clamp(22px, 2.6vw, 28px); max-width: 21ch; }
.orbit-centered .hero-description { color: var(--lab-ink); font-size: 13px; line-height: 1.7; margin: 16px 0 20px; }
.orbit-centered .hero-screen { width: 100%; max-width: 430px; margin: 0 auto; box-shadow: 6px 8px 0 var(--lab-line); }
.orbit-centered .software-actions { gap: 14px; }
.orbit-centered .software-actions a { font-size: 11px; }
.orbit-centered .lab-button { padding: 11px 14px; font-size: 12px; }
.orbit-centered .tiny-print { font-size: 9px; line-height: 1.6; margin-top: 14px; }
.orbit-centered .software-ticker { margin: 0 -28px; padding: 10px 18px; font-size: 10px; }
.orbit-centered .software-story,
.orbit-centered .software-editions,
.orbit-centered .software-screens { padding: 32px 0; }
.orbit-centered .software-story > h2,
.orbit-centered .edition-heading h2,
.orbit-centered .software-screens > h2 { font-size: clamp(24px, 3vw, 30px); margin: 10px 0 20px; max-width: 29ch; }
.orbit-centered .feature-row h3 { font-size: 16px; margin: 9px 0 7px; }
.orbit-centered .feature-row p,
.orbit-centered .section-intro { font-size: 12px; line-height: 1.7; }
.orbit-centered .section-intro { margin-bottom: 20px; max-width: 85ch; }
.orbit-centered .alpha-stamp { font-size: 11px; padding: 10px; }
.orbit-centered .edition-image { min-height: 240px; padding: 16px; }
.orbit-centered .edition-copy { padding: 20px; }
.orbit-centered .edition-copy h3 { font-size: 24px; }
.orbit-centered .edition-copy > p:not(.edition-tagline) { font-size: 13px; }
.orbit-centered .alpha-notice { margin-top: 22px; padding: 14px 18px; font-size: 11px; }
.orbit-centered .software-screen-grid { gap: 16px; }
.orbit-centered .software-screen-grid figure > button { height: 230px; padding: 12px; }
.orbit-centered .software-screen-grid figcaption { font-size: 10px; padding: 12px; }
.orbit-centered .software-next { margin-top: 24px; padding: 20px 0 0; }
.orbit-centered .software-next > a { font-size: 18px; }
@media (max-width: 850px) {
  .orbit-centered .software-hero { grid-template-columns: 1fr; gap: 24px; }
  .orbit-centered .hero-screen { max-width: 480px; }
  .orbit-centered .edition-image { height: 250px; min-height: 0; }
}
@media (max-width: 580px) {
  .software-launch.orbit-centered { width: calc(100% - 24px); padding: 0 16px 20px; margin-top: 12px; }
  .orbit-centered .software-nav { font-size: 9px; gap: 10px; }
  .orbit-centered .software-hero { padding: 24px 0; }
  .orbit-centered .software-intro h1 { font-size: 54px; }
  .orbit-centered .software-intro h2 { font-size: 24px; }
  .orbit-centered .software-ticker { margin: 0 -16px; }
  .orbit-centered .software-story,
  .orbit-centered .software-editions,
  .orbit-centered .software-screens { padding: 26px 0; }
  .orbit-centered .feature-row { gap: 18px; }
  .orbit-centered .software-screen-grid figure > button { min-height: 0; height: 210px; }
}

</style>
