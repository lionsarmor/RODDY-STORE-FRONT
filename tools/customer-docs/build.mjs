// Build customer PDF guides. Requires Playwright (installed in the local .tools environment).
import {chromium} from '../../.tools/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const manuals=JSON.parse(fs.readFileSync(new URL('./manuals.json',import.meta.url)));
const logo=fs.readFileSync('public/img/logos/RODDY_SVG_BRAND_PACK/full_logo/filled/roddy_full_white_red_filled.svg','utf8');
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
fs.mkdirSync('public/downloads/docs',{recursive:true});
const b=await chromium.launch({headless:true});
try {for(const m of manuals){
 const p=await b.newPage();
 const sections=m.pages.map((s,i)=>`<section><header>${logo}<span>RODDY / ${escape(m.edition)}</span></header><p class="eyebrow">${i===0?'CUSTOMER GUIDE':`${String(i+1).padStart(2,'0')} / ${escape(m.title)}`}</p><h1>${escape(s.title)}</h1>${s.image?`<img class="hero" src="data:image/png;base64,${fs.readFileSync('public/'+s.image).toString('base64')}">`:''}${s.blocks.map(x=>`<article>${x.title?`<h2>${escape(x.title)}</h2>`:''}${x.paragraphs.map(t=>`<p>${escape(t)}</p>`).join('')}</article>`).join('')}<footer>RODDY.WORLD · support@roddy.world <span>${i+1} / ${m.pages.length}</span></footer></section>`).join('');
 await p.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;color:#202329}section{width:210mm;min-height:297mm;padding:16mm 18mm 22mm;position:relative;break-after:page}section:last-child{break-after:auto}header{display:flex;align-items:center;justify-content:space-between;border-bottom:2px solid #c32d28;padding-bottom:9mm;margin-bottom:9mm}header svg{width:46mm;height:14mm}header span{font-size:8pt;color:#666;max-width:95mm;text-align:right}h1{font-size:28pt;line-height:1.05;letter-spacing:-.7px;margin:0 0 7mm}h2{font-size:13pt;line-height:1.2;margin:6mm 0 2mm}p{font-size:10.3pt;line-height:1.5;margin:0 0 3mm;white-space:pre-line}article{break-inside:avoid}.eyebrow{font-size:8pt;color:#a42625;letter-spacing:1.5px}.hero{width:100%;height:88mm;object-fit:contain;background:#f1f2f3;border-radius:3mm;margin:0 0 4mm}footer{position:absolute;bottom:12mm;left:18mm;right:18mm;border-top:1px solid #ddd;padding-top:3mm;font-size:8pt;color:#666}footer span{float:right}</style></head><body>${sections}</body></html>`);
 await p.evaluate(()=>Promise.all([...document.images].map(i=>i.decode())));
 const heights=await p.locator('section').evaluateAll(xs=>xs.map(x=>x.getBoundingClientRect().height));
 if(heights.some(h=>h>1124))throw new Error('Guide page overflow '+m.file+' '+heights);
 await p.pdf({path:'public/downloads/docs/'+m.file,printBackground:true,preferCSSPageSize:true});
 console.log(m.file,m.pages.length+' pages');await p.close();
}}finally{await b.close();}
