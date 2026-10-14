<script setup>
import {computed, nextTick, onMounted, reactive, ref, watch} from "vue";
import {useCatalogStore} from "../stores/catalog";
import {useCustomerStore} from "../stores/customer";
import {useRouter, useRoute} from "vue-router";
import {SUPPORT_EMAIL, SALES_EMAIL, contactRecipient, contactMailto, forumRequest} from "../forum-api.js";
import CommunityHero from "../components/CommunityHero.vue";
import RoddyLogo from "../components/RoddyLogo.vue";

const catalog = useCatalogStore();
const customer = useCustomerStore(), router = useRouter(), route = useRoute();
const endpoint = computed(() => catalog.settings.checkoutEndpoint);
const topics = ref([]), selected = ref(null), replies = ref([]);
const moreTopics = ref(false), moreReplies = ref(false);
const loading = ref(false), busy = ref(false), error = ref(""), notice = ref("");
const token = computed(() => customer.session?.token || "");
const handle = computed(() => customer.signedIn ? customer.profile.handle : "");
const draft = reactive({title: "", body: ""});
const reply = ref(""), composing = ref(false);
const emailDialog = ref(null), threadHeading = ref(null);
const email = reactive({category: "Issue", subject: "", name: "", body: ""});
const emailRecipient = computed(() => contactRecipient(email.category));
const copied = ref("");
const boardHeading = ref(null);
let restoredReturn = false;
let sequence = 0;
const date = value => new Date(value * 1000).toLocaleString();
const request = (path, body) => forumRequest(endpoint.value, path, token.value, body);

async function action(fn) {
  busy.value = true; error.value = ""; notice.value = "";
  try { await fn(); }
  catch (e) {
    error.value = e.message;
    if (e.status === 401 && token.value) customer.remember(null);
    if (e.status === 404) { selected.value = null; replies.value = []; }
  } finally { busy.value = false; }
}
async function loadTopics(append = false) {
  const before = append ? topics.value.at(-1)?.id || 0 : 0;
  const data = await request(`/forum/topics?before=${before}`);
  topics.value = append ? [...topics.value, ...data.topics] : data.topics;
  moreTopics.value = data.hasMore;
}
async function loadBoard() {
  if (!endpoint.value || loading.value) return;
  loading.value = true; error.value = "";
  try {
    await loadTopics();
    try { await customer.load(); } catch { /* Visitors can still read public topics. */ }
    if (!restoredReturn && route.query.board === '1') {
      restoredReturn = true;
      if (/^[1-9][0-9]{0,14}$/.test(route.query.topic || '')) await openTopic(Number(route.query.topic), false, false);
      else if (route.query.compose === '1' && handle.value) composing.value = true;
      await nextTick(); jumpToBoard();
    }
  }
  catch (e) { error.value = e.message; }
  finally { loading.value = false; }
}
async function openTopic(id, append = false, focus = true) {
  const current = ++sequence;
  const before = append ? replies.value[0]?.id || 0 : 0;
  const data = await request(`/forum/topics/${id}?before=${before}`);
  if (current !== sequence) return;
  selected.value = data.topic;
  topics.value = topics.value.map(topic => topic.id === id ? {...topic, replyCount: data.topic.replyCount, locked: data.topic.locked} : topic);
  replies.value = append ? [...data.replies, ...replies.value] : data.replies;
  moreReplies.value = data.hasMore;
  composing.value = false;
  if (!append && focus) {
    reply.value = "";
    await nextTick();
    threadHeading.value?.focus();
  }
}
function back() {
  sequence++; selected.value = null; replies.value = []; reply.value = ""; error.value = "";
}
function openAuth(compose = false) {
  compose = compose === true;
  router.push({path:'/account', query:{return:'community', ...(selected.value ? {topic:String(selected.value.id)} : compose ? {compose:'1'} : {})}});
}
function logout() {
  return action(async () => {
    await customer.logout(); draft.title = ''; draft.body = ''; reply.value = ''; composing.value = false;
    notice.value = 'Signed out of your RODDY account on this browser.';
  });
}
function createTopic() {
  return action(async () => {
    const result = await request("/forum/topics", draft);
    draft.title = ""; draft.body = "";
    await loadTopics(); await openTopic(result.topicId);
    notice.value = "Your topic is public. Thanks for joining in.";
  });
}
function addReply() {
  return action(async () => {
    const id = selected.value.id;
    await request(`/forum/topics/${id}/replies`, {body: reply.value});
    reply.value = "";
    // Reload the visible thread. Older long threads retain their pagination.
    const data = await request(`/forum/topics/${id}`);
    selected.value = data.topic; replies.value = data.replies; moreReplies.value = data.hasMore;
    topics.value = topics.value.map(topic => topic.id === id ? {...topic, replyCount: data.topic.replyCount} : topic);
    notice.value = "Reply posted.";
  });
}
function openEmail() {
  copied.value = ""; emailDialog.value.showModal();
}
function jumpToBoard() {
  boardHeading.value?.scrollIntoView({block: "start"});
  boardHeading.value?.focus({preventScroll: true});
}
function sendEmail() {
  window.location.href = contactMailto(email.category, email.subject, email.name, email.body);
  copied.value = "Your email app has been requested. Review and send the email there. If it did not open, copy the message below into your webmail.";
}
async function copyMessage() {
  try {
    await navigator.clipboard.writeText(`To: ${emailRecipient.value}\nSubject: [RODDY / ${email.category}] ${email.subject.trim()}\n\n${email.body.trim()}${email.name.trim() ? `\n\nFrom: ${email.name.trim()}` : ""}`);
    copied.value = "Email draft copied. Paste it into your email app and send.";
  } catch { copied.value = `Copy your message manually and email ${emailRecipient.value}.`; }
}
onMounted(async () => {
  if (endpoint.value) await loadBoard();
});
watch(endpoint, async value => {
  if (!value) return;
  await loadBoard();
});
</script>

<template>
  <article class="contact-page">
    <CommunityHero masthead="RODDY / CONTACT & COMMUNITY" edition="AN OPEN INVITATION TO THE CURIOUS" kicker="GOOD QUESTIONS WELCOME" note="A QUESTION. A HALF-FINISHED IDEA. A VERY GOOD WHAT IF. THERE’S ROOM FOR ALL OF IT HERE.">
      <template #title>GOOD QUESTIONS.<br /><em>START HERE.</em></template>
      <template #description>Something you’re making? Something we could do better? Pull up a chair. We’d love to hear it.</template>
      <template #actions>
        <button class="button primary" @click="openEmail">Contact RODDY privately ↗</button>
        <button class="text-button" @click="jumpToBoard">Meet the community ↓</button>
      </template>
      <template #art>
        <div class="contact-switchboard">
          <div class="switchboard-heading"><RoddyLogo kind="badge" /><span>DEPARTMENT OF<br />GOOD CONVERSATIONS</span></div>
          <div class="switchboard-screen">
            <span class="eyebrow">THE RODDY SWITCHBOARD</span>
            <div class="switchboard-message"><span aria-hidden="true">↗</span><p>HELLO,<br /><strong>CURIOUS HUMAN.</strong><span class="switchboard-cursor" aria-hidden="true">_</span></p></div>
            <p class="switchboard-note">THREE WAYS TO KEEP IN TOUCH. YOUR CALL.</p>
          </div>
          <div class="switchboard-lines">
            <button @click="openEmail"><span class="switchboard-number">01</span><span><strong>PRIVATE EMAIL</strong><small>A direct line to Roddy.</small></span><span aria-hidden="true">↗</span></button>
            <button @click="jumpToBoard"><span class="switchboard-number">02</span><span><strong>THE NOTICEBOARD</strong><small>A little company for your curiosity.</small></span><span aria-hidden="true">↓</span></button>
            <RouterLink to="/newsletter"><span class="switchboard-number">03</span><span><strong>POSTCARDS FROM RODDY</strong><small>Fresh signals. Very occasionally.</small></span><span aria-hidden="true">↗</span></RouterLink>
          </div>
          <div class="switchboard-footer"><span>INDEPENDENT TECHNOLOGY.</span><span>HUMAN CONVERSATIONS.</span></div>
        </div>
      </template>
    </CommunityHero>

    <section class="contact-intro" aria-label="Choose how to get in touch">
      <div class="contact-margin-note"><span>01 / FIND YOUR PEOPLE</span><span>GOOD COMPANY.<br />SHARED CURIOSITY.</span></div>
      <div><h2>A little community corner.</h2><p>Show us your build. Ask the question you’ve been sitting on. Join the General board with the same RODDY account you use in the shop.</p><button class="text-button" @click="jumpToBoard">Take a look around ↓</button></div>
      <div><h2>Some things are personal.</h2><p>Need a hand with a product or an existing order? <a :href="`mailto:${SUPPORT_EMAIL}`">{{SUPPORT_EMAIL}}</a>.</p><p>Sales, new-order inquiries or a collaboration? <a :href="`mailto:${SALES_EMAIL}`">{{SALES_EMAIL}}</a>.</p><button class="text-button" @click="openEmail">Open the contact form ↗</button></div>
    </section>

    <div class="contact-board-wrap">
    <section class="forum-board" aria-labelledby="forum-heading" :aria-busy="loading || busy">
      <div class="forum-toolbar">
        <div><p class="eyebrow">02 / THE COMMUNITY / GENERAL</p><h2 id="forum-heading" ref="boardHeading" tabindex="-1">THE NOTICEBOARD<span>.</span></h2></div>
        <div class="forum-actions">
          <template v-if="handle"><RouterLink to="/account" class="forum-handle">@{{handle}} · My account</RouterLink><button class="text-button" :disabled="busy" @click="logout">Sign out</button></template>
          <button v-else class="button" @click="openAuth">Create account / Sign in</button>
          <button class="button" :disabled="loading || busy" @click="action(() => selected ? openTopic(selected.id, false, false) : loadTopics())">Refresh</button>
        </div>
      </div>
      <p class="forum-guideline">One RODDY account for the shop and noticeboard. Only your handle appears here; your saved addresses stay private. Posts are public. Be kind, stay curious, and keep passwords, order numbers and personal details out of the board. Use private email for those.</p>
      <p v-if="error" class="notice" role="alert">{{error}}</p>
      <p v-if="notice" class="notice" role="status">{{notice}}</p>
      <p v-if="loading" class="empty-state" role="status">Loading the community board…</p>
      <template v-else-if="selected">
        <button class="text-button" :disabled="busy" @click="back">← All topics</button>
        <article class="forum-thread">
          <p class="eyebrow forum-thread-label">A CONVERSATION WORTH HAVING <span aria-hidden="true">↗</span></p>
          <div class="forum-post-meta"><span>@{{selected.handle}} <strong v-if="selected.owner">RODDY</strong></span><time :datetime="new Date(selected.created*1000).toISOString()">{{date(selected.created)}}</time></div>
          <h3 ref="threadHeading" tabindex="-1">{{selected.title}}</h3>
          <p class="forum-body">{{selected.body}}</p>
          <p v-if="selected.locked" class="notice">This topic is closed to new replies.</p>
        </article>
        <h3 class="forum-replies-heading">{{selected.replyCount}} {{selected.replyCount === 1 ? 'reply' : 'replies'}}</h3>
        <button v-if="moreReplies" class="button" :disabled="busy" @click="action(() => openTopic(selected.id, true))">Load earlier replies</button>
        <article v-for="post in replies" :key="post.id" class="forum-reply">
          <div class="forum-post-meta"><span>@{{post.handle}} <strong v-if="post.owner">RODDY</strong></span><time :datetime="new Date(post.created*1000).toISOString()">{{date(post.created)}}</time></div>
          <p class="forum-body">{{post.body}}</p>
        </article>
        <form v-if="handle && !selected.locked" class="forum-form" @submit.prevent="addReply">
          <div class="forum-compose-heading"><p class="eyebrow">KEEP THE CONVERSATION GOING</p><h3>Your turn.</h3></div>
          <label>Reply as @{{handle}}<textarea v-model="reply" rows="5" maxlength="1800" required placeholder="Join the conversation…" /></label>
          <div class="forum-form-footer"><small>{{reply.length}} / 1800 · public reply</small><button class="button primary" :disabled="busy || !reply.trim()">{{busy ? 'Posting…' : 'Post reply'}}</button></div>
        </form>
        <p v-else-if="!handle && !selected.locked" class="forum-signin-prompt"><button class="text-button" @click="openAuth">Create an account or sign in</button> to reply.</p>
      </template>
      <template v-else>
        <div class="forum-new-topic"><div><h3>Every good idea starts somewhere.</h3><p>A question, a build, a bit of feedback. Make yourself at home.</p></div><button class="button primary" :disabled="busy" @click="handle ? composing = !composing : openAuth(true)">{{composing ? 'Close draft' : 'Start a topic +'}}</button></div>
        <form v-if="composing && handle" class="forum-form" @submit.prevent="createTopic">
          <div class="forum-compose-heading"><p class="eyebrow">NEW TOPIC / PUBLIC CONVERSATION</p><h3>Put an idea out there.</h3></div>
          <label>Topic title<input v-model="draft.title" maxlength="100" required placeholder="What would you like to talk about?" /></label>
          <label>Your post<textarea v-model="draft.body" rows="6" maxlength="1800" required placeholder="Ask a question or share a comment…" /></label>
          <div class="forum-form-footer"><small>{{draft.body.length}} / 1800 · public post</small><button class="button primary" :disabled="busy || !draft.title.trim() || !draft.body.trim()">{{busy ? 'Posting…' : 'Post topic'}}</button></div>
        </form>
        <div v-if="topics.length" class="forum-topic-list">
          <button v-for="(topic, index) in topics" :key="topic.id" class="forum-topic" :disabled="busy" @click="action(() => openTopic(topic.id))">
            <span class="forum-topic-index" aria-hidden="true">{{String(index + 1).padStart(2, '0')}}</span>
            <span><strong>{{topic.title}}</strong><small>@{{topic.handle}} <b v-if="topic.owner">· RODDY</b> · {{date(topic.created)}}</small></span><span class="forum-topic-count">{{topic.replyCount}} {{topic.replyCount === 1 ? 'reply' : 'replies'}}<small v-if="topic.locked">Closed</small><span aria-hidden="true">↗</span></span>
          </button>
        </div>
        <div v-else-if="!error" class="forum-empty"><span class="forum-empty-mark" aria-hidden="true">✳</span><p class="eyebrow">A BLANK PAGE IS A BEGINNING.</p><h3>Room for the<br /><em>first good question.</em></h3><p>No topics yet. Say hello with your RODDY account.</p><button class="text-button" @click="handle ? composing = true : openAuth(true)">{{handle ? 'Start the first topic ↗' : 'Create account / Sign in ↗'}}</button></div>
        <button v-if="moreTopics" class="button" :disabled="busy" @click="action(() => loadTopics(true))">Load older topics</button>
      </template>
    </section>
    <p class="contact-board-signoff"><span>BE KIND. STAY CURIOUS. MAKE SOMETHING.</span><span>THAT’S THE SPIRIT.</span></p>
    </div>

    <section class="contact-postcards" aria-labelledby="contact-postcards-heading">
      <div><p class="eyebrow">03 / KEEP A LITTLE SIGNAL IN YOUR INBOX</p><h2 id="contact-postcards-heading">FROM OUR WORKBENCH.<br /><em>TO YOUR WORLD.</em></h2><p>New builds, new releases and the occasional shop special. Postcards from our corner of the future, only when there’s something to share.</p><RouterLink to="/newsletter" class="button primary">Postcards from RODDY ↗</RouterLink></div>
      <div class="contact-postcards-seal"><RoddyLogo kind="full_logo" /><span>LOW FREQUENCY.<br />HIGH CURIOSITY.</span><small>NO NEED TO KEEP UP.<br />JUST KEEP WONDERING.</small></div>
    </section>

    <dialog ref="emailDialog" class="contact-dialog" aria-labelledby="email-heading" @click="e => e.target === emailDialog && emailDialog.close()">
      <div class="dialog-heading"><p class="eyebrow">A DIRECT LINE / PRIVATE EMAIL</p><button class="dialog-close" aria-label="Close contact dialog" @click="emailDialog.close()">×</button></div>
      <div class="dialog-brand"><RoddyLogo kind="badge" /><span>HUMAN TO HUMAN.<br />IDEA TO POSSIBILITY.</span></div>
      <h2 id="email-heading">What’s on<br /><em>your mind?</em></h2>
      <p>Your message goes to <a :href="`mailto:${emailRecipient}`">{{emailRecipient}}</a>. Choose what it’s about below, then review and send the message in your email app. It does not post to the forum.</p>
      <form class="forum-form" @submit.prevent="sendEmail">
        <div class="email-fields"><label>What’s it about?<select v-model="email.category"><option>Issue</option><option>Existing order</option><option>Concern</option><option>Suggestion</option><option>Sales inquiry</option><option>New order inquiry</option><option>Collaboration</option><option>Other</option></select></label><label>Your name (optional)<input v-model="email.name" autocomplete="name" maxlength="80" /></label></div>
        <label>Subject<input v-model="email.subject" maxlength="120" required placeholder="A few words about your message" /></label>
        <label>Message<textarea v-model="email.body" rows="7" maxlength="4000" required placeholder="Tell me what happened, what you’re thinking, or what we could make together…" /></label>
        <div class="forum-actions"><button class="button primary">Open email app ↗</button><button class="button" type="button" @click="copyMessage">Copy email draft</button></div>
        <p v-if="copied" class="notice" role="status">{{copied}}</p>
      </form>
    </dialog>
  </article>
</template>

<style scoped>
.contact-page {max-width:1280px;margin-inline:auto;overflow-wrap:anywhere;}
.contact-page .button {min-height:44px;}
.contact-page a {text-decoration:underline;text-underline-offset:4px;}
.contact-switchboard {border:1px solid var(--color-text);padding:20px;background:var(--color-panel);box-shadow:8px 8px 0 var(--rule);transform:rotate(2deg);}
.switchboard-heading {display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:18px;}
.switchboard-heading .roddy-logo {width:65px;height:auto;}
.switchboard-heading>span {font:8px/1.8 var(--font-mono);letter-spacing:.06em;text-align:right;}
.switchboard-screen {border:1px solid var(--rule);padding:19px;background:var(--color-bg);}
.switchboard-screen>.eyebrow {font-size:8px;}
.switchboard-message {display:flex;align-items:center;gap:18px;margin:25px 0;}
.switchboard-message>span {font:64px/1 var(--font-sans);color:var(--color-brand);}
.switchboard-message p {font:14px/1.8 var(--font-mono);}
.switchboard-message strong {font-weight:700;}
.switchboard-cursor {color:var(--color-brand);}
.switchboard-note {font:8px/1.8 var(--font-mono);color:var(--color-text-dim);}
.switchboard-lines {margin-top:18px;}
.switchboard-lines :is(button,a) {width:100%;display:grid;grid-template-columns:30px minmax(0,1fr) 20px;gap:12px;align-items:center;text-align:left;padding:15px 0;border-bottom:1px solid var(--rule);text-decoration:none;transition:padding .2s,background .2s;}
.switchboard-lines :is(button,a):hover {padding-inline:8px;background:var(--color-bg-alt);}
.switchboard-number {font:13px var(--font-mono);color:var(--color-brand);}
.switchboard-lines strong {display:block;font:10px/1.6 var(--font-mono);letter-spacing:.03em;}
.switchboard-lines small {display:block;font:12px/1.6 var(--font-sans);color:var(--color-text-dim);margin-top:3px;}
.switchboard-lines :is(button,a)>span:last-child {font-size:22px;}
.switchboard-footer {display:flex;justify-content:space-between;gap:15px;font:7px/1.8 var(--font-mono);margin-top:17px;}
.contact-intro {display:grid;grid-template-columns:.8fr 1.2fr 1.2fr;gap:38px;padding:65px 32px;}
.contact-margin-note {display:flex;flex-direction:column;gap:26px;font:9px/1.8 var(--font-mono);letter-spacing:.04em;}
.contact-margin-note>span:first-child {color:var(--color-text-dim);}
.contact-margin-note>span:last-child {font-size:12px;}
.contact-intro h2 {font:750 27px/1.15 var(--font-sans);letter-spacing:-.04em;margin-bottom:18px;}
.contact-intro p {color:var(--color-text-dim);font-size:14px;line-height:1.9;margin-bottom:20px;}
.inline-contact-link {text-decoration:underline;text-underline-offset:4px;color:var(--color-text);}
.contact-intro small {font:8px/1.8 var(--font-mono);letter-spacing:.04em;}
.contact-board-wrap {margin:0 32px 65px;}
.forum-board {border:1px solid var(--color-text);background:var(--color-panel);padding:clamp(20px,4vw,40px);box-shadow:7px 7px 0 var(--rule);}
.forum-toolbar,.forum-new-topic,.forum-form-footer,.forum-post-meta {display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;}
.forum-toolbar h2 {font:850 clamp(29px,4.4vw,53px)/1.05 var(--font-sans);margin-top:14px;letter-spacing:-.055em;scroll-margin-top:180px;}
.forum-toolbar h2>span {color:var(--color-brand);}
.forum-actions {display:flex;gap:12px;align-items:center;flex-wrap:wrap;}
.forum-handle {padding:8px 11px;border:1px solid var(--rule);font:11px var(--font-mono);}
.forum-guideline {margin:28px 0;padding:18px 0;border-block:1px solid var(--rule);font-size:12px;line-height:1.8;color:var(--color-text-dim);}
.forum-new-topic {margin:30px 0;}
.forum-new-topic h3 {font-size:19px;font-weight:650;letter-spacing:-.025em;}
.forum-new-topic p {font-size:13px;line-height:1.7;color:var(--color-text-dim);margin-top:6px;}
.forum-topic-list {border-top:1px solid var(--rule);margin:30px 0;}
.forum-topic {display:grid;grid-template-columns:36px minmax(0,1fr) auto;align-items:center;gap:20px;width:100%;text-align:left;padding:26px 10px;border-bottom:1px solid var(--rule);transition:background .2s;}
.forum-topic:hover {background:var(--color-bg-alt);}
.forum-topic-index {font:19px var(--font-mono);color:var(--color-brand);}
.forum-topic strong {font:700 21px/1.35 var(--font-sans);letter-spacing:-.025em;display:block;}
.forum-topic small {display:block;margin-top:8px;color:var(--color-text-dim);font-size:12px;line-height:1.6;}
.forum-topic-count {font:10px/1.6 var(--font-mono);text-align:right;}
.forum-topic-count>span {display:block;font:26px var(--font-sans);margin-top:8px;color:var(--color-brand);}
.forum-empty {position:relative;text-align:center;padding:48px 20px;background:var(--color-bg-alt);border:1px solid var(--rule);}
.forum-empty-mark {display:block;font:55px/1 var(--font-sans);color:var(--color-brand);margin-bottom:24px;}
.forum-empty>.eyebrow {font-size:8px;}
.forum-empty h3 {font:750 clamp(28px,4vw,42px)/1.15 var(--font-sans);letter-spacing:-.045em;margin:20px 0;}
.forum-empty h3 em,.contact-dialog h2 em,.contact-postcards h2 em {font-style:normal;text-decoration:underline;text-decoration-color:var(--color-brand);text-underline-offset:5px;text-decoration-thickness:3px;}
.forum-empty p:not(.eyebrow),.forum-form small {color:var(--color-text-dim);font-size:12px;line-height:1.8;}
.forum-empty .text-button {margin-top:24px;}
.forum-form {display:grid;gap:20px;margin:28px 0;padding:26px;background:var(--color-bg-alt);border:1px solid var(--rule);}
.forum-compose-heading {padding-bottom:18px;border-bottom:1px solid var(--rule);}
.forum-compose-heading .eyebrow {font-size:8px;}
.forum-compose-heading h3 {font:750 28px/1.2 var(--font-sans);letter-spacing:-.04em;margin-top:12px;}
.forum-form label {display:grid;gap:10px;font-size:13px;font-weight:600;min-width:0;}
.forum-form input,.forum-form textarea,.forum-form select {width:100%;min-width:0;background:var(--color-panel);color:var(--color-text);border:1px solid var(--rule);padding:13px;font:inherit;font-size:16px;font-weight:400;line-height:1.6;}
.forum-form input::placeholder,.forum-form textarea::placeholder {color:var(--color-text-dim);opacity:.85;}
.forum-form textarea {resize:vertical;min-height:120px;}
.forum-form :is(input,textarea,select):focus {outline:2px solid var(--color-brand);outline-offset:2px;}
.forum-thread {padding:30px 0;border-bottom:1px solid var(--rule);}
.forum-thread-label {display:flex;align-items:center;justify-content:space-between;color:var(--color-text-dim);font-size:8px;margin-bottom:24px;}
.forum-thread-label>span {font:32px var(--font-sans);color:var(--color-brand);}
.forum-thread h3 {font:750 clamp(27px,4.2vw,46px)/1.15 var(--font-sans);letter-spacing:-.045em;margin:24px 0;}
.forum-body {white-space:pre-wrap;overflow-wrap:anywhere;font-size:16px;line-height:1.9;}
.forum-post-meta {color:var(--color-text-dim);font:10px/1.8 var(--font-mono);}
.forum-post-meta strong {border:1px solid var(--rule);padding:3px 6px;font-size:9px;margin-left:8px;color:var(--color-text);}
.forum-replies-heading {font:500 11px/1.6 var(--font-mono);text-transform:uppercase;letter-spacing:.08em;margin:32px 0 8px;}
.forum-reply {padding:24px;border:1px solid var(--rule);background:var(--color-bg-alt);margin-top:16px;}
.forum-reply .forum-body {margin-top:16px;}
.forum-signin-prompt {margin-top:28px;padding:22px;background:var(--color-bg-alt);font-size:14px;line-height:1.8;}
.contact-board-signoff {display:flex;justify-content:space-between;gap:16px;margin-top:24px;font:8px/1.8 var(--font-mono);letter-spacing:.06em;color:var(--color-text-dim);}
.contact-postcards {display:grid;grid-template-columns:2fr 1fr;gap:65px;padding:55px 45px;background:var(--color-bg-alt);border-top:1px solid var(--color-text);}
.contact-postcards h2 {font:850 clamp(30px,4vw,49px)/1.1 var(--font-sans);letter-spacing:-.055em;margin:25px 0;}
.contact-postcards p:not(.eyebrow) {font-size:15px;line-height:1.9;color:var(--color-text-dim);max-width:52ch;margin-bottom:28px;}
.contact-postcards a {text-decoration:none;}
.contact-postcards-seal {display:flex;flex-direction:column;align-items:flex-start;gap:28px;border-left:1px solid var(--rule);padding:12px 0 0 35px;}
.contact-postcards-seal .roddy-logo {width:min(100%,210px);height:auto;}
.contact-postcards-seal>span {font:13px/1.9 var(--font-mono);}
.contact-postcards-seal small {font:8px/1.9 var(--font-mono);letter-spacing:.05em;margin-top:auto;color:var(--color-text-dim);}
.contact-dialog {color:var(--color-text);background:linear-gradient(90deg,var(--spectrum-1) 0% 16.66%,var(--spectrum-2) 16.66% 33.33%,var(--spectrum-3) 33.33% 50%,var(--spectrum-4) 50% 66.66%,var(--spectrum-5) 66.66% 83.33%,var(--spectrum-6) 83.33%) top/100% 7px no-repeat,var(--color-panel);border:1px solid var(--color-text);box-shadow:8px 8px 0 #0003;padding:clamp(20px,4vw,36px);max-width:640px;width:calc(100% - 32px);max-height:calc(100dvh - 40px);overflow:auto;overscroll-behavior:contain;margin:auto;}
.contact-dialog::backdrop {background:rgb(0 0 0 / .72);backdrop-filter:blur(3px);}
.dialog-heading {position:sticky;top:-1px;z-index:1;background:var(--color-panel);display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:22px;padding:8px 0;}
.dialog-heading .eyebrow {font-size:9px;}
.dialog-close {border:1px solid var(--rule);width:44px;height:44px;flex-shrink:0;font-size:27px;line-height:1;}
.dialog-brand {display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:25px;}
.dialog-brand .roddy-logo {width:64px;height:auto;}
.dialog-brand>span {font:8px/1.8 var(--font-mono);text-align:right;letter-spacing:.04em;}
.contact-dialog h2 {font:800 clamp(32px,5vw,44px)/1.12 var(--font-sans);letter-spacing:-.045em;margin-bottom:20px;}
.contact-dialog>p {font-size:14px;color:var(--color-text-dim);line-height:1.8;}
.contact-dialog a {text-decoration:underline;text-underline-offset:4px;}
.contact-dialog .forum-form {padding:0;border:0;background:transparent;margin-bottom:0;}
.email-fields {display:grid;grid-template-columns:1fr 1fr;gap:18px;}
@media(max-width:1050px){.contact-intro{grid-template-columns:1fr 1fr;gap:30px;}.contact-margin-note{grid-column:1/-1;flex-direction:row;justify-content:space-between;align-items:center;}.contact-margin-note>span:last-child{text-align:right;}.forum-toolbar{align-items:flex-start;}.forum-toolbar>.forum-actions{margin-top:8px;}.contact-postcards{gap:35px;}}
@media(max-width:800px){.contact-switchboard{transform:none;box-shadow:5px 5px 0 var(--rule);}.contact-intro{padding:42px 24px;}.contact-board-wrap{margin:0 24px 45px;}.contact-postcards{padding:42px 24px;gap:30px;grid-template-columns:1fr;}.contact-postcards-seal{border-left:0;border-top:1px solid var(--rule);padding:24px 0 0;display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:center;}.contact-postcards-seal small{grid-column:1/-1;}.contact-board-signoff>span:last-child{display:none;}}
@media(max-width:600px){.contact-intro{grid-template-columns:1fr;gap:30px;}.contact-margin-note{gap:20px;}.contact-margin-note>span:last-child{font-size:10px;}.forum-board{padding:20px 16px;}.forum-actions{gap:10px;}.forum-actions .button{font-size:10px;padding:11px 12px;}.forum-toolbar h2{font-size:clamp(27px,7vw,38px);}.forum-new-topic{gap:20px;}.forum-new-topic .button,.forum-form-footer .button{width:100%;}.forum-form{padding:20px 14px;}.email-fields{grid-template-columns:1fr;}.forum-topic{grid-template-columns:22px minmax(0,1fr) auto;gap:12px;padding:22px 0;align-items:start;}.forum-topic-index{font-size:14px;padding-top:3px;}.forum-topic strong{font-size:17px;}.forum-topic-count{max-width:60px;}.forum-topic small{font-size:10px;}.forum-reply{padding:20px 16px;}.forum-empty{padding:36px 12px;}.switchboard-footer{font-size:6px;}.contact-dialog .forum-actions>.button{width:100%;}.contact-dialog .forum-form{padding:0;}}
@media(max-width:360px){.contact-board-wrap{margin-inline:18px;}.contact-switchboard{padding:16px;}.switchboard-screen{padding:14px;}.switchboard-message{gap:12px;}.switchboard-message p{font-size:12px;}.contact-postcards h2{font-size:27px;}}
</style>
