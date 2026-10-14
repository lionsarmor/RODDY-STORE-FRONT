import x16 from '../backend/keycap_templates/x16-v06-cherry-tkl.json' with {type: 'json'};

// One validated template per physical layout. Profiles are catalog data and
// can share a layout while offering different defaults and allowed options.
export const KEYCAP_TEMPLATES = {[x16.id]: x16};
export const MARKS = {'commander-x16':'Commander X16 butterfly','otter-x':'OtterX X','roddy-x':'RODDY flight X','roddy-r':'RODDY R + dot'};
export const ARROWS = {'small-black':'Small black arrows','bold-white':'Bold white arrows'};
export const DEFAULT_COLORS = {alpha:'#F7F7F5',modifiers:'#50545E',accents:'#7FAFD3'};
export const DEFAULT_SELECTION = {...DEFAULT_COLORS,mark:'commander-x16',arrows:'small-black'};
export function profileFor(catalog, product) {
  return catalog.keycapProfiles?.find(p=>p.id===product?.keycaps?.profileId) || null;
}
export function defaultDesign(profile) {
  return {profileId:profile.id,revision:profile.revision,...DEFAULT_SELECTION,...profile.defaults};
}
export function designKey(design) {
  return design ? JSON.stringify(['profileId','revision','alpha','modifiers','accents','mark','arrows'].map(k=>design[k] || '')) : '';
}
export function designError(design, profile) {
  if (!profile || !KEYCAP_TEMPLATES[profile.templateId]) return 'This keyboard profile is unavailable.';
  if (!design || design.profileId!==profile.id || design.revision!==profile.revision) return 'This design needs refreshing on the product page.';
  if (!['alpha','modifiers','accents'].every(k=>/^#[0-9A-F]{6}$/.test(design[k] || ''))) return 'Choose valid key colors.';
  if (!(profile.marks || Object.keys(MARKS)).includes(design.mark) || !(profile.arrows || Object.keys(ARROWS)).includes(design.arrows)) return 'Choose an available symbol and arrow style.';
  return '';
}
const isDark = hex => {
  const rgb=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4);
  return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]<.179;
};
export function generateDesign(profile, selection) {
  const error=designError(selection,profile);if(error)throw new Error(error);
  const template=KEYCAP_TEMPLATES[profile.templateId],out=structuredClone(template.base);
  out.name=`RODDY ${profile.name} ${selection.mark} ${selection.arrows}`;
  for(const [id,key] of Object.entries(out.keys)){
    const color=selection[template.meta[id].group];key.colorId=color;
    key.layers=key.layers.map(l=>({...l,colorId:['#F7F7F5','#0A0D12'].includes(l.colorId)?(isDark(color)?'#F7F7F5':'#0A0D12'):l.colorId}));
    if(template.meta[id].sourceKey==='COMMANDER')key.layers=structuredClone(template.marks[selection.mark]);
    if(template.arrows[id])key.layers=structuredClone(selection.arrows==='bold-white'?template.arrows[id]:template.base.keys[id].layers);
  }
  return out;
}
export function designLabel(d) {
  return d ? `${d.alpha} / ${d.modifiers} / ${d.accents} · ${MARKS[d.mark] || d.mark} · ${ARROWS[d.arrows] || d.arrows}` : '';
}
export function downloadJson(value, name) {
  const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
