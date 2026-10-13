<script setup>
import {onMounted, reactive, ref, watch} from "vue";
import {SUPPORT_EMAIL, SALES_EMAIL} from "../forum-api.js";
import {commerceRequest} from "./commerce-api";
const props = defineProps({endpoint: String, token: String, connected: Boolean});
const topics = ref([]), selected = ref(null), replies = ref([]);
const moreTopics = ref(false), moreReplies = ref(false), busy = ref(false), writing = ref(false);
const error = ref(""), status = ref(""), reply = ref("");
const draft = reactive({title: "", body: ""});
const date = value => new Date(value * 1000).toLocaleString();
const request = (path, body) => commerceRequest(props.endpoint, path, props.token, body);
async function run(fn) {
  busy.value = true; error.value = ""; status.value = "";
  try { await fn(); } catch (e) { error.value = e.message; }
  finally { busy.value = false; }
}
async function load(append = false) {
  const data = await request(`/admin/forum/topics?before=${append ? topics.value.at(-1)?.id || 0 : 0}`);
  if (!props.connected) return;
  topics.value = append ? [...topics.value, ...data.topics] : data.topics;
  moreTopics.value = data.hasMore;
}
async function open(id, older = false) {
  const data = await request(`/admin/forum/topics/${id}?before=${older ? replies.value[0]?.id || 0 : 0}`);
  if (!props.connected) return;
  selected.value = data.topic; replies.value = older ? [...data.replies, ...replies.value] : data.replies;
  moreReplies.value = data.hasMore;
}
function moderateTopic(key, value) {
  return run(async () => {
    await request(`/admin/forum/topics/${selected.value.id}/moderate`, {[key]: value});
    await open(selected.value.id); await load(); status.value = "Topic updated.";
  });
}
function moderateReply(post) {
  return run(async () => {
    await request(`/admin/forum/replies/${post.id}/moderate`, {hidden: !post.hidden});
    await open(selected.value.id); status.value = "Reply visibility updated.";
  });
}
function moderateHandle(post) {
  return run(async () => {
    await request(`/admin/forum/users/${post.authorId}/moderate`, {banned: !post.banned});
    await open(selected.value.id); await load(); status.value = "Handle posting access updated. Existing sessions were revoked.";
  });
}
function publishTopic() {
  return run(async () => {
    const data = await request("/admin/forum/topics", draft);
    draft.title = ""; draft.body = ""; writing.value = false;
    await load(); await open(data.topicId); status.value = "Posted publicly as RODDY.";
  });
}
function publishReply() {
  return run(async () => {
    await request(`/admin/forum/topics/${selected.value.id}/replies`, {body: reply.value});
    reply.value = ""; await open(selected.value.id); status.value = "Reply posted publicly as RODDY.";
  });
}
watch(() => props.connected, connected => {
  if (connected) run(load);
  else {topics.value = []; selected.value = null; replies.value = []; reply.value = "";}
});
onMounted(() => {if (props.connected) run(load);});
</script>
<template>
  <section class="forum-admin">
    <p class="help-copy">One public General board lives on the contact page. Post or reply as the verified RODDY owner, hide spam, close discussions and disable abusive handles. Hidden content stays available here for review; disabled handles lose their active sessions. Private messages go through visitors’ email apps to {{ SUPPORT_EMAIL }} for help, or {{ SALES_EMAIL }} for sales, new-order inquiries and collaborations.</p>
    <div class="admin-actions"><button class="button" :disabled="!connected || busy" @click="run(async () => {await load(); if(selected) await open(selected.id);})">Refresh forum</button><button class="button" :disabled="!connected || busy" @click="writing = !writing">{{writing ? 'Close draft' : 'Post as RODDY +'}}</button><a href="./#/contact" target="_blank" rel="noopener noreferrer" class="button">Open public board ↗</a></div>
    <p v-if="error" class="notice" role="alert">{{error}}</p><p v-if="status" class="notice" role="status">{{status}}</p>
    <form v-if="writing" class="form-grid forum-admin-compose" @submit.prevent="publishTopic"><label class="full">Topic title<input v-model="draft.title" maxlength="100" required /></label><label class="full">Public post<textarea v-model="draft.body" rows="6" maxlength="1800" required /></label><button class="button primary" :disabled="busy || !draft.title.trim() || !draft.body.trim()">Publish as RODDY</button></form>
    <div class="forum-admin-layout">
      <div><h3>Topics</h3><button v-for="topic in topics" :key="topic.id" class="forum-admin-topic" :class="{'is-selected': selected?.id === topic.id}" :disabled="busy" @click="run(() => {reply = ''; return open(topic.id);})"><strong>{{topic.title}}</strong><small>@{{topic.handle}} · {{topic.replyCount}} replies<br />{{topic.hidden ? 'Hidden' : 'Public'}} · {{topic.locked ? 'Closed' : 'Open'}}</small></button><button v-if="moreTopics" class="button small" :disabled="busy" @click="run(() => load(true))">Load older topics</button><p v-if="!topics.length" class="help-copy">{{connected ? 'No topics yet. You can post a welcome message as RODDY.' : 'Connect with your GitHub owner account to manage the board.'}}</p></div>
      <div v-if="selected">
        <article class="forum-admin-post" :class="{moderated:selected.hidden}"><div class="field-heading"><h3>{{selected.title}}</h3><span>{{selected.hidden ? 'Hidden' : 'Public'}}</span></div><p class="help-copy">@{{selected.handle}} · {{date(selected.created)}}{{selected.banned ? ' · posting disabled' : ''}}</p><p class="forum-admin-body">{{selected.body}}</p><div class="admin-actions"><button class="button small" :disabled="busy" @click="moderateTopic('hidden', !selected.hidden)">{{selected.hidden ? 'Restore topic' : 'Hide topic'}}</button><button class="button small" :disabled="busy" @click="moderateTopic('locked', !selected.locked)">{{selected.locked ? 'Reopen replies' : 'Close replies'}}</button><button v-if="!selected.owner" class="button small" :disabled="busy" @click="moderateHandle(selected)">{{selected.banned ? 'Enable' : 'Disable'}} @{{selected.handle}}</button></div></article>
        <button v-if="moreReplies" class="button small" :disabled="busy" @click="run(() => open(selected.id, true))">Load earlier replies</button>
        <article v-for="post in replies" :key="post.id" class="forum-admin-post" :class="{moderated:post.hidden}"><p class="help-copy">@{{post.handle}}{{post.owner ? ' · RODDY owner' : ''}} · {{date(post.created)}}{{post.hidden ? ' · hidden' : ''}}{{post.banned ? ' · posting disabled' : ''}}</p><p class="forum-admin-body">{{post.body}}</p><div class="admin-actions"><button class="button small" :disabled="busy" @click="moderateReply(post)">{{post.hidden ? 'Restore reply' : 'Hide reply'}}</button><button v-if="!post.owner" class="button small" :disabled="busy" @click="moderateHandle(post)">{{post.banned ? 'Enable' : 'Disable'}} @{{post.handle}}</button></div></article>
        <form v-if="!selected.hidden && !selected.locked" class="form-grid forum-admin-compose" @submit.prevent="publishReply"><label class="full">Reply publicly as RODDY<textarea v-model="reply" rows="5" maxlength="1800" required /></label><button class="button primary" :disabled="busy || !reply.trim()">Post RODDY reply</button></form><p v-else class="help-copy">Restore and reopen this topic to add a public reply.</p>
      </div>
    </div>
  </section>
</template>
<style scoped>
.forum-admin-layout {display:grid;grid-template-columns:minmax(200px,1fr) minmax(0,2fr);gap:24px;margin-top:28px;}
.forum-admin-topic {display:block;text-align:left;width:100%;border:1px solid var(--color-border);padding:16px;margin:12px 0;overflow-wrap:anywhere;}
.forum-admin-topic small {display:block;margin-top:8px;line-height:1.7;color:var(--color-text-dim);}
.is-selected {border-color:var(--color-brand);}
.forum-admin-post {padding:20px;border:1px solid var(--color-border);margin-bottom:16px;overflow-wrap:anywhere;}
.forum-admin-body {white-space:pre-wrap;line-height:1.7;margin:18px 0;}
.forum-admin-compose {margin:24px 0;}
.moderated {border-style:dashed;}
@media(max-width:850px){.forum-admin-layout{grid-template-columns:1fr;}}
</style>
