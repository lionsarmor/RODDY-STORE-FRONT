import document from '../backend/keycap_palette.json' with {type:'json'};
import legacyColors from '../backend/keycap_color_map.json' with {type:'json'};
export const KEYCAP_COLORS=document.colors;
export const PALETTE=Object.freeze(Object.assign(Object.create(null),Object.fromEntries(KEYCAP_COLORS.map(c=>[c.id,c]))));
export const colorHex=id=>PALETTE[id]?.hex || '#808080';
export const colorName=id=>PALETTE[id] ? `${PALETTE[id].name} · ${id}` : id;
// Only catalog defaults migrate. Customer/order input must already use palette IDs.
export const catalogColorId=value=>PALETTE[value]?value:legacyColors[value?.toUpperCase()] || value;
export const DARK_INK='GR001';
export const LIGHT_INK='GR002';
export function legendColorId(id){
  const rgb=[1,3,5].map(i=>parseInt(colorHex(id).slice(i,i+2),16)/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4);
  return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]<.179?LIGHT_INK:DARK_INK;
}
