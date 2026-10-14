import {PALETTE,colorHex,colorName,catalogColorId,legendColorId} from './keycap-palette.js';
import markOptions from '../backend/keycap_mark_options.json' with {type: 'json'};
import x16 from './keycap-previews/x16-v06-cherry-tkl.json' with {type: 'json'};

// One validated template per physical layout. Profiles are catalog data and
// can share a layout while offering different defaults and allowed options.
export const KEYCAP_PREVIEWS = {[x16.id]: x16};
export const DISABLED_MARKS = Object.keys(markOptions).filter(id=>markOptions[id].enabled===false);
export const MARKS = Object.fromEntries(Object.entries(markOptions).filter(([,option])=>option.enabled!==false).map(([id,option])=>[id,option.label]));
export const MARK_DESCRIPTIONS = Object.fromEntries(Object.entries(markOptions).map(([id,option])=>[id,option.inspiration || '']));
export const ARROWS = {'small-black':'Small black arrows','bold-white':'Bold white arrows'};
export const DEFAULT_COLORS = {alpha:'GR002',modifiers:'GR009',accents:'BL003'};
export const DEFAULT_SELECTION = {...DEFAULT_COLORS,mark:'roddy-r',arrows:'small-black',keyColors:{}};
export const availableMarks = profile => (profile?.marks || Object.keys(MARKS)).filter(id=>MARKS[id]);
export function profileFor(catalog, product) {
  return catalog.keycapProfiles?.find(p=>p.id===product?.keycaps?.profileId) || null;
}
export function defaultDesign(profile) {
  const design={profileId:profile.id,revision:profile.revision,...DEFAULT_SELECTION,...profile.defaults};
  for(const group of ['alpha','modifiers','accents'])design[group]=catalogColorId(design[group]);
  design.keyColors=JSON.parse(JSON.stringify(profile.defaults?.keyColors || {}));
  const marks=availableMarks(profile);
  if(!marks.includes(design.mark))design.mark=marks.includes(DEFAULT_SELECTION.mark)?DEFAULT_SELECTION.mark:marks[0];
  return design;
}
export function designKey(design) {
  return design ? JSON.stringify([...['profileId','revision','alpha','modifiers','accents','mark','arrows'].map(k=>design[k] || ''),Object.entries(design.keyColors || {}).sort(([a],[b])=>a.localeCompare(b))]) : '';
}
export function designError(design, profile) {
  if (!profile || !KEYCAP_PREVIEWS[profile.templateId]) return 'This keyboard profile is unavailable.';
  if (!design || design.profileId!==profile.id || design.revision!==profile.revision) return 'This design needs refreshing on the product page.';
  if (!['alpha','modifiers','accents'].every(k=>PALETTE[design[k]])) return 'Choose colors from the Yuzu palette.';
  const overrides=design.keyColors;
  const ids=new Set(KEYCAP_PREVIEWS[profile.templateId].keys.map(k=>k.id));
  if(!overrides || typeof overrides!=='object' || Array.isArray(overrides) || Object.keys(overrides).length>256 || Object.entries(overrides).some(([key,color])=>!ids.has(key)||!PALETTE[color])) return 'Choose valid individual keys and Yuzu palette colors.';
  if (!availableMarks(profile).includes(design.mark) || !(profile.arrows || Object.keys(ARROWS)).includes(design.arrows)) return 'Choose an available symbol and arrow style.';
  return '';
}
// Display geometry only. Supplier layouts, IDs and manufacturing JSON stay on
// the droplet and are never imported into a customer or admin JavaScript bundle.
export function generatePreview(profile, selection) {
  const error=designError(selection,profile);if(error)throw new Error(error);
  const template=KEYCAP_PREVIEWS[profile.templateId];
  const keys=template.keys.map(key=>{
    const paletteId=selection.keyColors[key.id] || selection[key.group];
    const color=colorHex(paletteId);
    let shapes=key.shapes.map(s=>({...s,fill:s.inkRole==='auto'?colorHex(legendColorId(paletteId)):s.fill}));
    if(key.commander)shapes=template.marks[selection.mark];
    if(key.boldArrows)shapes=selection.arrows==='bold-white'?key.boldArrows:key.shapes;
    return {id:key.id,name:key.name,label:key.label,x:key.x,y:key.y,width:key.width,color,paletteId,custom:!!selection.keyColors[key.id],shapes};
  });
  return {width:template.width,height:template.height,keys};
}
export function designLabel(d) {
  return d ? `${colorName(d.alpha)} / ${colorName(d.modifiers)} / ${colorName(d.accents)} · ${MARKS[d.mark] || d.mark} · ${ARROWS[d.arrows] || d.arrows}${Object.keys(d.keyColors || {}).length?' · '+Object.keys(d.keyColors).length+' individual key colors':''}` : '';
}
