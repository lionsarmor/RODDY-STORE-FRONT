<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { commerceRequest } from './commerce-api';
const props = defineProps({ endpoint: String, token: String, connected: Boolean });
const data = ref(null), error = ref(''), busy = ref(false), opening = ref('');
const project = ref('all'), search = ref(''), archives = ref(false), readyLink = ref('');
const groups = computed(() => {
  const query = search.value.toLowerCase().trim();
  const entries = (data.value?.entries || []).filter(e =>
    (project.value === 'all' || e.project === project.value || e.project === 'shared') &&
    (archives.value || !e.archive) &&
    (!query || `${e.title} ${e.description} ${e.group} ${e.project}`.toLowerCase().includes(query)));
  return [...new Set(entries.map(e => e.group))].map(title => ({ title, entries: entries.filter(e => e.group === title) }));
});
async function load() {
  if (!props.connected) return;
  busy.value = true; error.value = '';
  try { data.value = await commerceRequest(props.endpoint, '/admin/workshop', props.token); }
  catch (e) { error.value = e.message; }
  finally { busy.value = false; }
}
async function open(entry) {
  // Reserve the tab during the user gesture, before the authenticated request.
  const win = window.open('about:blank', '_blank');
  if (win) win.opener = null;
  opening.value = entry.id; error.value = ''; readyLink.value = '';
  try {
    const result = await commerceRequest(props.endpoint, '/admin/workshop/open', props.token, { id: entry.id });
    const url = new URL(result.path, props.endpoint).href;
    if (win) win.location.replace(url); else readyLink.value = url;
  } catch (e) { if (win) win.close(); error.value = e.message; }
  finally { opening.value = ''; }
}
watch(() => [props.connected, props.endpoint, props.token], () => {
  data.value = null; readyLink.value = ''; load();
});
onMounted(load);
</script>

<template>
  <section class="workshop">
    <div class="workshop-heading"><div><p class="eyebrow">RODDY / PROJECT LIBRARY</p><h2>Everything for the next build.</h2><p>Open purchasing packs, board files, cases and artwork in one place.</p></div><button class="button small" :disabled="!connected || busy" @click="load">{{ busy ? 'Loading…' : 'Refresh library' }}</button></div>
    <p v-if="!connected" class="notice">Connect your owner GitHub account to open the private project library.</p>
    <p v-if="error" class="notice error" role="alert">{{ error }}</p>
    <p v-if="readyLink" class="notice">Your browser blocked the new tab. <a :href="readyLink" target="_blank" rel="noopener noreferrer">Open your project document ↗</a></p>
    <template v-if="data && connected">
      <div class="workshop-filters"><label>Project<select v-model="project" aria-label="Project"><option value="all">All projects</option><option v-for="p in data.projects" :key="p.id" :value="p.id">{{ p.name }}</option></select></label><label class="workshop-search">Find a document<input v-model="search" type="search" placeholder="Try: 10 devices, PCBWay, shell, branding…" /></label><label class="check"><input v-model="archives" type="checkbox" />Show older revisions & concepts</label></div>
      <p class="help-copy">Library updated {{ new Date(data.updatedAt).toLocaleString() }}. These are uploaded project snapshots. Document access expires after two hours; reopen here for a fresh link.</p>
      <p v-if="!groups.length" class="notice">No documents match these filters.</p>
      <section v-for="group in groups" :key="group.title" class="workshop-group"><h3>{{ group.title }}</h3><div class="workshop-grid"><article v-for="entry in group.entries" :key="entry.id" class="workshop-card"><p class="eyebrow">{{ entry.project === 'shared' ? 'BOTH PROJECTS' : data.projects.find(p => p.id === entry.project)?.name }} <span v-if="entry.archive"> / ARCHIVE</span></p><h4>{{ entry.title }}</h4><p>{{ entry.description }}</p><button class="button small" :disabled="!!opening" @click="open(entry)">{{ opening === entry.id ? 'Opening…' : 'Open ↗' }}</button></article></div></section>
    </template>
  </section>
</template>

<style scoped>
.workshop-heading{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap;margin-bottom:24px}.workshop-heading h2{font-size:clamp(26px,3vw,42px);line-height:1.15;margin:12px 0}.workshop-heading p:last-child{font-size:14px;opacity:.75}.workshop-filters{display:flex;gap:18px;align-items:end;flex-wrap:wrap;padding:20px 0}.workshop-filters label:not(.check){display:grid;gap:8px;font-size:12px}.workshop-search{flex:1;min-width:220px}.workshop-filters input[type=search],.workshop-filters select{padding:12px;border:1px solid var(--color-border,#555);background:transparent;color:inherit}.workshop-filters select option{background:var(--color-bg,#161616)}.workshop-filters .check{font-size:12px;padding:12px 0}.help-copy{font-size:12px;opacity:.7;line-height:1.6}.workshop-group{margin-top:32px}.workshop-group h3{font-size:22px;margin-bottom:16px}.workshop-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:16px}.workshop-card{border:1px solid var(--color-border,#555);padding:23px;display:flex;flex-direction:column;align-items:start}.workshop-card h4{font-size:20px;line-height:1.25;margin:10px 0}.workshop-card>p:not(.eyebrow){font-size:13px;line-height:1.65;opacity:.8;margin-bottom:20px;flex:1}.workshop-card .eyebrow{font-size:10px}.workshop-card .eyebrow span{color:#e2a06f}.workshop .notice{padding:18px;border:1px solid #777;line-height:1.6}.workshop .error{border-color:#bd504d}
</style>
