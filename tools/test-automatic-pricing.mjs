// Component regression using fixture responses only; never accesses supplier APIs.
import {chromium} from '../.tools/node_modules/playwright/index.mjs';
import {createServer} from 'vite';
import assert from 'node:assert/strict';
import {writeFileSync,unlinkSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
const entry='.tools/pricing-'+randomUUID()+'.mjs';
writeFileSync(entry,`import {createApp,h} from 'vue';import PricingManager from '../src/admin/PricingManager.vue';import '../src/styles/main.css';import '../src/admin/admin.css';createApp({render:()=>h(PricingManager,{endpoint:'https://pricing.test',token:'fixture',catalog:{products:[{id:'part',name:'Fixture product'}]}})}).mount('#app');`);
const server=await createServer({optimizeDeps:{noDiscovery:true,include:['vue']},server:{host:'127.0.0.1',port:0},plugins:[{name:'pricing-fixture',configureServer(server){server.middlewares.use('/__pricing_test',(_req,res)=>{res.setHeader('Content-Type','text/html');res.end(`<html><body><div id="app"></div><script type="module" src="/${entry}"></script></body></html>`);});}}]});
await server.listen();const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage({viewport:{width:1200,height:950}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 let settings={enabled:true,markupPercent:30,feePercent:4,feeFixed:.30,unknownTaxPercent:10,round99:true,revision:1},saves=0;
 await page.route('https://pricing.test/**',async route=>{
  assert.equal(new URL(route.request().url()).pathname,'/admin/pricing');
  if(route.request().method()==='POST'){const body=route.request().postDataJSON();assert.equal(body.revision,settings.revision);settings={...body,revision:body.revision+1};saves++;}
  await route.fulfill({json:{settings,prices:[{id:'part',variantId:'',priceCents:1099,landedCents:1350,shippingCents:800,available:true,checkedAt:1792135383}]}});
 });
 await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__pricing_test`);
 await page.getByText('Fixture product',{exact:true}).waitFor();
 assert.equal(await page.getByLabel('Markup on landed cost · %').inputValue(),'30');
 assert.match(await page.locator('table').innerText(),/\$13.50[\s\S]*\$10.99/);
 await page.getByLabel('Markup on landed cost · %').fill('35');
 await page.getByRole('button',{name:'Save pricing rules'}).click();
 await page.getByText(/Pricing rules saved/).waitFor();assert.equal(saves,1);assert.equal(settings.markupPercent,35);
 await page.getByRole('button',{name:'Refresh price status'}).click();await page.getByText('Fixture product',{exact:true}).waitFor();
 assert.equal(await page.getByLabel('Markup on landed cost · %').inputValue(),'35');
 await page.setViewportSize({width:390,height:844});
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Pricing controls must fit mobile');
 assert.deepEqual(errors,[]);console.log('PASS automatic pricing: saved adjustable markup, cost/status table, refresh persistence, mobile layout. Fixture APIs only.');
}finally{await browser.close();await server.close();unlinkSync(entry);}
