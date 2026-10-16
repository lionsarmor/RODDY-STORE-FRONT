// Component regression using fixture responses only; never accesses supplier APIs.
import {chromium} from '../.tools/node_modules/playwright/index.mjs';
import {createServer} from 'vite';
import assert from 'node:assert/strict';
import {writeFileSync,unlinkSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
const entry='.tools/pricing-'+randomUUID()+'.mjs';
writeFileSync(entry,`import {createApp,h} from 'vue';import {createPinia} from 'pinia';import {createRouter,createMemoryHistory} from 'vue-router';import PricingManager from '../src/admin/PricingManager.vue';import Cart from '../src/views/Cart.vue';import {useCatalogStore} from '../src/stores/catalog';import {useCartStore} from '../src/stores/cart';import {normalizeProduct} from '../src/catalog-model';import '../src/styles/main.css';import '../src/admin/admin.css';
const pinia=createPinia(),router=createRouter({history:createMemoryHistory(),routes:[{path:'/',component:Cart}]});
const catalog=useCatalogStore(pinia);catalog.loaded=true;catalog.settings.checkoutEndpoint='https://pricing.test';catalog.settings.checkoutEnabled=true;catalog.products=[normalizeProduct({id:'part',name:'Fixture product',price:9.99,active:true,status:'available',type:'physical',trackStock:false,fulfillment:'automatic',shippingCountries:['US']})];useCartStore(pinia).items=[{id:'part',qty:2}];
createApp({render:()=>new URLSearchParams(location.search).has('cart')?h(Cart):h(PricingManager,{endpoint:'https://pricing.test',token:'fixture',catalog})}).use(pinia).use(router).mount('#app');`);
const server=await createServer({optimizeDeps:{noDiscovery:true,include:['vue']},server:{host:'127.0.0.1',port:0},plugins:[{name:'pricing-fixture',configureServer(server){server.middlewares.use('/__pricing_test',(_req,res)=>{res.setHeader('Content-Type','text/html');res.end(`<html><body><div id="app"></div><script type="module" src="/${entry}"></script></body></html>`);});}}]});
await server.listen();const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage({viewport:{width:1200,height:950}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 let settings={enabled:true,markupPercent:30,feePercent:4,feeFixed:.30,unknownTaxPercent:10,round99:true,revision:1},saves=0;
 await page.route('https://pricing.test/**',async route=>{
  if(new URL(route.request().url()).pathname==='/quote'){
   assert.equal(route.request().method(),'POST');assert.equal(route.request().postDataJSON().items[0].qty,2);
   await route.fulfill({json:{quoteId:'fixture',subtotal:2398,shipping:800,amountTotal:3198,items:[{id:'part',variantId:'',qty:2,unitPriceCents:1199}]}});return;
  }
  assert.equal(new URL(route.request().url()).pathname,'/admin/pricing','No checkout or supplier submission permitted');
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
 await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__pricing_test?cart=1`);
 await page.getByRole('heading',{name:'YOUR CART.'}).waitFor();
 assert.ok(await page.getByRole('button',{name:'Update prices & shipping'}).isEnabled(),'Automatic supplier item must allow quotes');
 for(const [label,value] of Object.entries({'First name':'Test','Last name':'Buyer','Email':'test@example.com','Phone':'2025550100','Address':'1600 Pennsylvania Ave NW','City':'Washington','State / province code':'DC','ZIP / postal code':'20500'}))await page.getByLabel(label,{exact:true}).fill(value);
 await page.getByRole('button',{name:'Update prices & shipping'}).click();
 await page.getByText('Total to pay',{exact:true}).waitFor();
 assert.match(await page.locator('body').innerText(),/\$11.99 each/);assert.match(await page.locator('body').innerText(),/\$31.98/);
 assert.ok(await page.getByRole('button',{name:'Checkout as guest ↗'}).isEnabled());
 await page.getByLabel('City',{exact:true}).fill('Alexandria');
 assert.ok(await page.getByRole('button',{name:'Checkout as guest ↗'}).isDisabled(),'Address change invalidates accepted quote');
 assert.deepEqual(errors,[]);console.log('PASS automatic pricing: saved adjustable markup, cost/status table, refresh persistence, mobile layout; automatic cart permits quotes and displays revised unit price/total before payment. Fixture APIs only.');
}finally{await browser.close();await server.close();unlinkSync(entry);}
