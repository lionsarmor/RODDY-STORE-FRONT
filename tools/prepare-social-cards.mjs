// Prepare fixed-size HTML artwork for browser rendering to 1200 × 630 JPEGs.
// Source photographs stay separate from generated socialImage files, so reruns
// never put an old sharing card inside a new one. No customer data is involved.
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {publicProducts,escapeHtml as e,productImage} from '../src/social-previews.js';
import {productOrigin} from '../src/product-origin.js';
const catalog=JSON.parse(await readFile('public/data/products.json','utf8'));
const output='.tools/social-cards';await mkdir(output,{recursive:true});
const roddySource=await readFile('public/img/logos/RODDY_SVG_BRAND_PACK/full_logo/outline/roddy_full_classic_cream_red_outline.svg','utf8');
const roddy=roddySource.match(/<g[\s\S]*<\/g>/)[0].replaceAll('fill="#000000"','fill="currentColor"');
const x16Source=await readFile('public/img/commander-x16/logo-color.svg','utf8');
const x16=x16Source.match(/<g id="Rectangle_Color">([\s\S]*)<\/g>/)[1].replace(/<path fill="#10192F"[\s\S]*?\/>/,'').replaceAll('fill="#FFFFFF"','fill="currentColor"');
const preferred={
 'x16-keycaps':'img/products/x16-v06-roddy-keycap-pile.png',
 'plan-9-original-and-x16':'img/products/plan-9-vhs-render-social.png',
};
const titles={
 'roddy-de10-nano':'DE10-NANO DEV KIT',
 'usb-c-power-supply-5v-3a':'5V / 3A USB-C POWER',
 'link-commander-snap-fit-enclosure':'LINK COMMANDER CASE FILES',
 'plan-9-original-and-x16':'PLAN 9 FROM OUTER SPACE',
};
const manifest=[];
for(const p of publicProducts(catalog)){
 const isX16=['x16-keycaps','link-commander-e'].includes(p.id);
 const image=preferred[p.id] || new URL(productImage({...p,socialImage:undefined})).pathname.slice(1);
 const label=p.id==='x16-keycaps'?'KEYCAPS':'LINK COMMANDER';
 const name=titles[p.id]||p.name.trim();
 const status=p.betaAccess?'ALPHA · INVITED TESTERS':p.status==='coming-soon'?'IN DEVELOPMENT · NOT YET FOR SALE':p.type==='digital'?'DIGITAL DOWNLOAD':p.madeToOrder||p.keycaps||p.merch?'MADE TO ORDER':'EXPLORE THE PRODUCT';
 const description=(p.id==='keychain-kreatures'?'A pocket-sized companion from RODDY. In development; details and pricing to be announced.':p.shortDescription) || (p.id==='aula-f87-pro'?'Wireless mechanical keyboard · 87 keys · Hot-swappable switches.':'');
 const heading=isX16?`<span class="partner">OFFICIAL PARTNER</span><svg class="x16" viewBox="730 380 6770 725">${x16}</svg><h1 class="x16-name">${label}</h1>`:`<h1>${e(name)}</h1>`;
 const html=`<!doctype html><html lang="en"><meta charset="utf-8"><title>${e(p.name)} sharing artwork</title><style>
 @font-face{font-family:X16;src:url('/fonts/michroma/Michroma-Regular.ttf')}
 *{box-sizing:border-box}html,body{margin:0;width:1200px;height:630px;overflow:hidden}body{background:#f7f3e8;color:#242823;font-family:Arial,sans-serif}
 header{height:87px;margin:0 38px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #24282340}header svg{width:158px;height:45px}header span{font:700 13px monospace;letter-spacing:.13em;text-transform:uppercase}
 main{display:grid;grid-template-columns:600px 1fr;gap:38px;padding:26px 38px;height:475px}.photo{background:#e8e5dc;border:1px solid #24282322;display:flex;align-items:center;justify-content:center;overflow:hidden}.photo img{width:100%;height:100%;object-fit:contain}
 .copy{display:flex;flex-direction:column;justify-content:center;min-width:0}.origin{font:700 11px/1.4 monospace;letter-spacing:.1em;color:#5d6259;margin:0 0 19px}h1{font-size:42px;font-weight:800;line-height:1.04;letter-spacing:-.035em;margin:0;text-wrap:balance}.partner{font:700 13px/1.2 monospace;letter-spacing:.12em}.x16{width:100%;height:auto;display:block}.x16-name{font:400 29px/1.25 X16,sans-serif;letter-spacing:.025em;white-space:nowrap;-webkit-text-stroke:.4px currentColor}
 .description{font:19px/1.4 Arial,sans-serif;margin:22px 0 0;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}.status{font:700 11px/1.5 monospace;letter-spacing:.06em;border-top:1px solid #24282340;padding-top:15px;margin-top:22px;color:#9d2722}
 footer{height:68px;margin:0 38px;border-top:2px solid #242823;display:flex;align-items:center;justify-content:space-between;font:700 14px monospace;letter-spacing:.08em}footer b{color:#b42b27}
 </style><body><header><svg viewBox="233.5 263.6 1012.2 285.4" aria-label="RODDY">${roddy}</svg><span>${e(p.category)} / THE RODDY COLLECTION</span></header><main><div class="photo"><img src="/${e(image)}" alt="${e(p.name)}"></div><div class="copy"><p class="origin">${e(productOrigin(p).label)}</p><div>${heading}</div><p class="description">${e(description)}</p><p class="status">${status}</p></div></main><footer><span>RODDY.WORLD</span><span>PLAY. BUILD. MAKE IT YOURS. <b>↗</b></span></footer></body></html>`;
 await writeFile(`${output}/${p.id}.html`,html);
 manifest.push({id:p.id,source:image,html:`/${output}/${p.id}.html`,image:p.socialImage?.startsWith('img/social/products/')?p.socialImage:`img/social/products/${p.id}-v1.jpg`});
}
await writeFile(`${output}/manifest.json`,JSON.stringify(manifest,null,2)+'\n');
console.log(`Prepared ${manifest.length} product sharing cards in ${output}. Render at 1200 × 630 before publishing.`);
