<script setup>
import {computed, nextTick, onMounted, reactive, ref, watch} from "vue";
import {useCatalogStore} from "../stores/catalog";
import {CONTACT_EMAIL, contactMailto, forumRequest} from "../forum-api.js";

const catalog = useCatalogStore();
const endpoint = computed(() => catalog.settings.checkoutEndpoint);
const topics = ref([]), selected = ref(null), replies = ref([]);
const moreTopics = ref(false), moreReplies = ref(false);
const loading = ref(false), busy = ref(false), error = ref(""), notice = ref("");
const token = ref(""), handle = ref(""), register = ref(true);
const credentials = reactive({handle: "", password: ""});
const draft = reactive({title: "", body: ""});
const reply = ref(""), composing = ref(false);
const authDialog = ref(null), emailDialog = ref(null), threadHeading = ref(null);
const email = reactive({category: "Issue", subject: "", name: "", body: ""});
const copied = ref("");
const SESSION_KEY = "roddy:forum:session";
let sequence = 0;
const date = value => new Date(value * 1000).toLocaleString();
const request = (path, body) => forumRequest(endpoint.value, path, token.value, body);

function storeSession(data) {
  token.value = data?.token || "";
  handle.value = data?.handle || "";
  try {
    if (data) localStorage.setItem(SESSION_KEY, JSON.stringify(data));
    else localStorage.removeItem(SESSION_KEY);
  } catch { /* Posting still works when persistent storage is unavailable. */ }
}
async function action(fn) {
  busy.value = true; error.value = ""; notice.value = "";
  try { await fn(); }
  catch (e) {
    error.value = e.message;
    if (e.status === 401 && token.value) storeSession(null);
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
    if (token.value) {
      try { handle.value = (await request("/forum/me")).handle; }
      catch (e) { if (e.status === 401) storeSession(null); }
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
function openAuth() {
  credentials.password = ""; error.value = "";
  authDialog.value.showModal();
}
function authenticate() {
  return action(async () => {
    const data = await request(register.value ? "/forum/register" : "/forum/login", credentials);
    storeSession(data); credentials.password = "";
    authDialog.value.close(); notice.value = `Signed in as @${data.handle}.`;
  });
}
function logout() {
  return action(async () => {
    try { await request("/forum/logout", {}); }
    finally {
      storeSession(null); draft.title = ""; draft.body = ""; reply.value = "";
      notice.value = "Signed out on this browser.";
    }
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
function sendEmail() {
  window.location.href = contactMailto(email.category, email.subject, email.name, email.body);
  copied.value = "Your email app has been requested. Review and send the email there. If it did not open, copy the message below into your webmail.";
}
async function copyMessage() {
  try {
    await navigator.clipboard.writeText(`To: ${CONTACT_EMAIL}\nSubject: [RODDY / ${email.category}] ${email.subject}\n\n${email.body}${email.name ? `\n\nFrom: ${email.name}` : ""}`);
    copied.value = "Email draft copied. Paste it into your email app and send.";
  } catch { copied.value = `Copy your message manually and email ${CONTACT_EMAIL}.`; }
}
onMounted(async () => {
  try {
    const session = JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
    if (session?.expiresAt > Date.now() / 1000 && session.token) storeSession(session);
    else storeSession(null);
  } catch { storeSession(null); }
  if (endpoint.value) await loadBoard();
});
watch(endpoint, async value => {
  if (!value) return;
  await loadBoard();
});
</script>

<template>
  <article class="contact-page mx-auto max-w-6xl px-6 py-12">
    <p class="eyebrow">RODDY / GOOD QUESTIONS WELCOME</p>
    <header class="contact-hero">
      <div><h1>LET’S TALK<span>.</span></h1><p>Questions, comments, curious ideas. Pull up a chair.</p></div>
      <button class="button primary" @click="openEmail">Contact RODDY privately ↗</button>
    </header>
    <div class="contact-intro">
      <div><h2>A little community corner.</h2><p>Make a handle, ask a question, or share something with everyone. This is one General board for all things RODDY.</p></div>
      <div><h2>A direct line to me.</h2><p>Issues, concerns, suggestions or collaborations? <button class="text-button" @click="openEmail">Open the contact form</button> or email <a :href="`mailto:${CONTACT_EMAIL}`">{{CONTACT_EMAIL}}</a>.</p></div>
    </div>

    <section class="forum-board" aria-labelledby="forum-heading" :aria-busy="loading || busy">
      <div class="forum-toolbar">
        <div><p class="eyebrow">COMMUNITY / GENERAL</p><h2 id="forum-heading">THE NOTICEBOARD.</h2></div>
        <div class="forum-actions">
          <template v-if="handle"><span class="forum-handle">@{{handle}}</span><button class="text-button" :disabled="busy" @click="logout">Sign out</button></template>
          <button v-else class="button" @click="openAuth">Make a handle / Sign in</button>
          <button class="button" :disabled="loading || busy" @click="action(() => selected ? openTopic(selected.id, false, false) : loadTopics())">Refresh</button>
        </div>
      </div>
      <p class="forum-guideline">Posts are public. Be kind, stay curious, and keep passwords, order numbers and personal details out of the board. Use private email for those.</p>
      <p v-if="error && !authDialog?.open" class="notice" role="alert">{{error}}</p>
      <p v-if="notice" class="notice" role="status">{{notice}}</p>
      <p v-if="loading" class="empty-state" role="status">Loading the community board…</p>
      <template v-else-if="selected">
        <button class="text-button" :disabled="busy" @click="back">← All topics</button>
        <article class="forum-thread">
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
          <label>Reply as @{{handle}}<textarea v-model="reply" rows="5" maxlength="1800" required placeholder="Join the conversation…" /></label>
          <div class="forum-form-footer"><small>{{reply.length}} / 1800 · public reply</small><button class="button primary" :disabled="busy || !reply.trim()">{{busy ? 'Posting…' : 'Post reply'}}</button></div>
        </form>
        <p v-else-if="!handle && !selected.locked" class="forum-signin-prompt"><button class="text-button" @click="openAuth">Make a handle or sign in</button> to reply.</p>
      </template>
      <template v-else>
        <div class="forum-new-topic"><p>A question, a build, a bit of feedback—start here.</p><button class="button primary" :disabled="busy" @click="handle ? composing = !composing : openAuth()">{{composing ? 'Close draft' : 'Start a topic +'}}</button></div>
        <form v-if="composing && handle" class="forum-form" @submit.prevent="createTopic">
          <label>Topic title<input v-model="draft.title" maxlength="100" required placeholder="What would you like to talk about?" /></label>
          <label>Your post<textarea v-model="draft.body" rows="6" maxlength="1800" required placeholder="Ask a question or share a comment…" /></label>
          <div class="forum-form-footer"><small>{{draft.body.length}} / 1800 · public post</small><button class="button primary" :disabled="busy || !draft.title.trim() || !draft.body.trim()">{{busy ? 'Posting…' : 'Post topic'}}</button></div>
        </form>
        <div v-if="topics.length" class="forum-topic-list">
          <button v-for="topic in topics" :key="topic.id" class="forum-topic" :disabled="busy" @click="action(() => openTopic(topic.id))">
            <span><strong>{{topic.title}}</strong><small>@{{topic.handle}} <b v-if="topic.owner">· RODDY</b> · {{date(topic.created)}}</small></span><span class="forum-topic-count">{{topic.replyCount}} {{topic.replyCount === 1 ? 'reply' : 'replies'}}<small v-if="topic.locked">Closed</small><span aria-hidden="true">↗</span></span>
          </button>
        </div>
        <div v-else-if="!error" class="forum-empty"><span aria-hidden="true">✳</span><h3>Room for the first question.</h3><p>No topics yet. Make a handle and say hello.</p></div>
        <button v-if="moreTopics" class="button" :disabled="busy" @click="action(() => loadTopics(true))">Load older topics</button>
      </template>
    </section>

    <dialog ref="authDialog" class="contact-dialog" aria-labelledby="handle-heading" @click="e => e.target === authDialog && authDialog.close()" @close="credentials.password = ''; error = ''">
      <div class="dialog-heading"><p class="eyebrow">COMMUNITY / YOUR HANDLE</p><button class="dialog-close" aria-label="Close handle dialog" @click="authDialog.close()">×</button></div>
      <h2 id="handle-heading">{{register ? 'Make yourself at home.' : 'Welcome back.'}}</h2>
      <p>{{register ? 'Choose a public handle and a password to keep it yours. No email required.' : 'Sign in with your forum handle and password.'}}</p>
      <form class="forum-form" @submit.prevent="authenticate">
        <label>Handle<input v-model="credentials.handle" autocomplete="username" minlength="3" maxlength="24" pattern="[A-Za-z0-9_]{3,24}" required placeholder="Your_handle" /></label>
        <small>3–24 letters, numbers or underscores. Your handle appears on your posts.</small>
        <label>Password<input v-model="credentials.password" type="password" :autocomplete="register ? 'new-password' : 'current-password'" minlength="8" maxlength="128" required /></label>
        <small v-if="register">Keep your password safe. Email-based password recovery is not available yet. Stay signed in on this browser for up to 30 days; sign out on a shared device.</small>
        <p v-if="error" class="notice" role="alert">{{error}}</p>
        <button class="button primary" :disabled="busy">{{busy ? 'Please wait…' : register ? 'Create my handle' : 'Sign in'}}</button>
        <button type="button" class="text-button" :disabled="busy" @click="register = !register; error = ''; credentials.password = ''">{{register ? 'Already have a handle? Sign in' : 'New here? Make a handle'}}</button>
      </form>
    </dialog>

    <dialog ref="emailDialog" class="contact-dialog" aria-labelledby="email-heading" @click="e => e.target === emailDialog && emailDialog.close()">
      <div class="dialog-heading"><p class="eyebrow">A DIRECT LINE / PRIVATE EMAIL</p><button class="dialog-close" aria-label="Close contact dialog" @click="emailDialog.close()">×</button></div>
      <h2 id="email-heading">What’s on your mind?</h2>
      <p>Write directly to <a :href="`mailto:${CONTACT_EMAIL}`">{{CONTACT_EMAIL}}</a>. This opens your email app; review and send the message there. It does not post to the forum.</p>
      <form class="forum-form" @submit.prevent="sendEmail">
        <div class="email-fields"><label>What’s it about?<select v-model="email.category"><option>Issue</option><option>Concern</option><option>Suggestion</option><option>Collaboration</option><option>Other</option></select></label><label>Your name (optional)<input v-model="email.name" autocomplete="name" maxlength="80" /></label></div>
        <label>Subject<input v-model="email.subject" maxlength="120" required placeholder="A few words about your message" /></label>
        <label>Message<textarea v-model="email.body" rows="7" maxlength="4000" required placeholder="Tell me what happened, what you’re thinking, or what we could make together…" /></label>
        <div class="forum-actions"><button class="button primary">Open email app ↗</button><button class="button" type="button" @click="copyMessage">Copy email draft</button></div>
        <p v-if="copied" class="notice" role="status">{{copied}}</p>
      </form>
    </dialog>
  </article>
</template>

<style scoped>
.contact-page {overflow-wrap:anywhere;}
.contact-hero {display:flex;align-items:end;justify-content:space-between;gap:28px;margin:24px 0 48px;}
.contact-hero h1 {font-size:clamp(42px,8vw,88px);font-weight:800;line-height:1;letter-spacing:-.06em;margin-bottom:20px;}
.contact-hero h1 span {color:var(--color-brand);}
.contact-hero p,.contact-intro p,.contact-dialog p {color:var(--color-text-dim);line-height:1.7;}
.contact-intro {display:grid;grid-template-columns:1fr 1fr;gap:40px;padding:28px 0 48px;border-top:1px solid var(--color-border);}
.contact-intro h2 {font-size:22px;font-weight:700;margin-bottom:10px;}
.contact-page a {text-decoration:underline;text-underline-offset:4px;}
.forum-board {border:1px solid var(--color-border);background:var(--color-bg-alt);padding:clamp(18px,4vw,32px);}
.forum-toolbar,.forum-new-topic,.forum-form-footer,.forum-post-meta {display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;}
.forum-toolbar h2 {font-size:clamp(24px,4vw,36px);font-weight:800;margin-top:10px;letter-spacing:-.04em;}
.forum-actions {display:flex;gap:12px;align-items:center;flex-wrap:wrap;}
.forum-guideline {margin:24px 0;padding:16px 0;border-top:1px solid var(--color-border);border-bottom:1px solid var(--color-border);font-size:13px;line-height:1.7;color:var(--color-text-dim);}
.forum-new-topic {margin:24px 0;}
.forum-new-topic p {font-size:14px;color:var(--color-text-dim);}
.forum-topic-list {border-top:1px solid var(--color-border);margin:24px 0;}
.forum-topic {display:flex;align-items:center;justify-content:space-between;gap:18px;width:100%;text-align:left;padding:24px 0;border-bottom:1px solid var(--color-border);}
.forum-topic:hover {color:var(--color-brand);}
.forum-topic strong {font-size:18px;display:block;}
.forum-topic small {display:block;margin-top:8px;color:var(--color-text-dim);font-size:12px;line-height:1.6;}
.forum-topic-count {flex-shrink:0;font-size:12px;text-align:right;}
.forum-topic-count>span {display:block;font-size:24px;margin-top:10px;}
.forum-empty {text-align:center;padding:50px 16px;}
.forum-empty>span {font-size:40px;color:var(--color-brand);}
.forum-empty h3 {font-size:22px;font-weight:700;margin:14px 0;}
.forum-empty p,.forum-form small {color:var(--color-text-dim);font-size:13px;line-height:1.6;}
.forum-form {display:grid;gap:18px;margin-top:28px;}
.forum-form label {display:grid;gap:10px;font-size:13px;font-weight:600;min-width:0;}
.forum-form input,.forum-form textarea,.forum-form select {width:100%;min-width:0;background:var(--color-bg);color:var(--color-text);border:1px solid var(--color-border);padding:12px;font:inherit;font-weight:400;line-height:1.6;}
.forum-form textarea {resize:vertical;min-height:120px;}
.forum-form :is(input,textarea,select):focus {outline:2px solid var(--color-accent);outline-offset:2px;}
.forum-thread {padding:28px 0;border-bottom:1px solid var(--color-border);}
.forum-thread h3 {font-size:clamp(24px,4vw,36px);line-height:1.3;font-weight:750;margin:20px 0;}
.forum-body {white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.8;}
.forum-post-meta {color:var(--color-text-dim);font-size:12px;}
.forum-post-meta strong {border:1px solid var(--color-border);padding:3px 6px;font-size:10px;margin-left:8px;color:var(--color-text);}
.forum-replies-heading {font-size:16px;margin:28px 0 8px;font-weight:700;}
.forum-reply {padding:24px 0;border-bottom:1px solid var(--color-border);}
.forum-reply .forum-body {margin-top:14px;}
.forum-signin-prompt {margin-top:24px;}
.contact-dialog {color:var(--color-text);background:var(--color-bg);border:1px solid var(--color-border);padding:clamp(20px,4vw,36px);max-width:620px;width:calc(100% - 32px);max-height:calc(100dvh - 40px);overflow:auto;overscroll-behavior:contain;margin:auto;}
.contact-dialog::backdrop {background:rgb(0 0 0 / .7);}
.dialog-heading {position:sticky;top:0;z-index:1;background:var(--color-bg);display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:24px;padding:8px 0;}
.dialog-close {border:1px solid var(--color-border);width:36px;height:36px;flex-shrink:0;font-size:25px;line-height:1;}
.contact-dialog h2 {font-size:28px;font-weight:750;line-height:1.3;margin-bottom:16px;}
.email-fields {display:grid;grid-template-columns:1fr 1fr;gap:18px;}
@media(max-width:640px){.contact-hero{align-items:start;flex-direction:column;}.contact-intro{grid-template-columns:1fr;gap:24px;}.forum-toolbar{align-items:start;}.forum-actions .button{font-size:11px;}.email-fields{grid-template-columns:1fr;}.forum-topic{align-items:start;}.forum-topic-count{max-width:60px;}.forum-new-topic .button{width:100%;}.forum-form-footer .button{width:100%;}}
</style>
