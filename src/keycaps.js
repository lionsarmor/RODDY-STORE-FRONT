import x16 from './keycap-previews/x16-v06-cherry-tkl.json' with {type: 'json'};

// One validated template per physical layout. Profiles are catalog data and
// can share a layout while offering different defaults and allowed options.
export const KEYCAP_PREVIEWS = {[x16.id]: x16};
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
  if (!profile || !KEYCAP_PREVIEWS[profile.templateId]) return 'This keyboard profile is unavailable.';
  if (!design || design.profileId!==profile.id || design.revision!==profile.revision) return 'This design needs refreshing on the product page.';
  if (!['alpha','modifiers','accents'].every(k=>/^#[0-9A-F]{6}$/.test(design[k] || ''))) return 'Choose valid key colors.';
  if (!(profile.marks || Object.keys(MARKS)).includes(design.mark) || !(profile.arrows || Object.keys(ARROWS)).includes(design.arrows)) return 'Choose an available symbol and arrow style.';
  return '';
}
const isDark = hex => {
  const rgb=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4);
  return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]<.179;
};
// Display geometry only. Supplier layouts, IDs and manufacturing JSON stay on
// the droplet and are never imported into a customer or admin JavaScript bundle.
export function generatePreview(profile, selection) {
  const error=designError(selection,profile);if(error)throw new Error(error);
  const template=KEYCAP_PREVIEWS[profile.templateId];
  const keys=template.keys.map(key=>{
    const color=selection[key.group];
    let shapes=key.shapes.map(s=>({...s,fill:['#F7F7F5','#0A0D12'].includes(s.fill)?(isDark(color)?'#F7F7F5':'#0A0D12'):s.fill}));
    if(key.commander)shapes=template.marks[selection.mark];
    if(key.boldArrows)shapes=selection.arrows==='bold-white'?key.boldArrows:key.shapes;
    return {label:key.label,x:key.x,y:key.y,width:key.width,color,shapes};
  });
  return {width:template.width,height:template.height,keys};
}
export function designLabel(d) {
  return d ? `${d.alpha} / ${d.modifiers} / ${d.accents} · ${MARKS[d.mark] || d.mark} · ${ARROWS[d.arrows] || d.arrows}` : '';
}
