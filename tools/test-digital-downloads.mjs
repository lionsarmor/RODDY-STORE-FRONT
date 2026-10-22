// Fixture-only browser coverage: never sends real mail, creates purchases, or contacts suppliers.
import {chromium} from '../.tools/node_modules/playwright/index.mjs';
import {createServer} from 'vite';
import assert from 'node:assert/strict';
import {writeFileSync,unlinkSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
const entry='.tools/digital-downloads-'+randomUUID()+'.mjs';
writeFileSync(entry,`import {createApp,h,reactive} from 'vue';import {createPinia} from 'pinia';import OrderManager from '../src/admin/OrderManager.vue';import FreeDownload from '../src/components/FreeDownload.vue';import LiveProductPrice from '../src/admin/LiveProductPrice.vue';import {useCatalogStore} from '../src/stores/catalog';import '../src/styles/main.css';import '../src/admin/admin.css';
const pinia=createPinia(),catalog=useCatalogStore(pinia);catalog.loaded=true;catalog.settings.checkoutEndpoint='https://downloads.test';const product=reactive({id:'free-game',name:'FREE GAME'});window.fixtureProduct=product;
createApp({render:()=>{const view=new URLSearchParams(location.search).get('view');return view==='free'?h(FreeDownload,{product,url:'https://roddy.world/game.zip',label:'Free game'}):view==='price'?h(LiveProductPrice,{product:{id:'de10'},endpoint:'https://downloads.test',token:'fixture'}):h(OrderManager,{endpoint:'https://downloads.test',token:'fixture',connected:true});}}).use(pinia).mount('#app');`);
const server=await createServer({optimizeDeps:{noDiscovery:true,include:['vue']},server:{host:'127.0.0.1',port:0},plugins:[{name:'digital-download-fixture',configureServer(server){server.middlewares.use('/__digital_downloads',(_req,res)=>{res.setHeader('Content-Type','text/html');res.end(`<html><body><div id="app"></div><script type="module" src="/${entry}"></script></body></html>`);});}}]});
await server.listen();const browser=await chromium.launch({headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000},permissions:['clipboard-read','clipboard-write']});
const page=await context.newPage(),errors=[],calls=[];page.on('pageerror',e=>errors.push(e.message));
const now=Math.floor(Date.now()/1000),ticket='fixture-ticket';
const digital={id:'paid-order',created:now,amount_total:399,payment_status:'paid',items:[{id:'desk',name:'DESK COMMANDER',kind:'digital',qty:1}],fulfillments:[],finance:{captured:399,fees:0},messages:[],expenses:[]};
const free={...digital,id:'free-order',amount_total:0,payment_status:'free',messageContext:'fixture-context',address:{email:'sam@example.com',first_name:'Sam'},items:[{id:'free-game',name:'FREE GAME',kind:'free-digital',qty:1}],finance:{captured:0,fees:0}};
let failDownload=false;
try{
 await page.route('https://downloads.test/**',async route=>{
  const request=route.request(),url=new URL(request.url());calls.push({path:url.pathname,method:request.method(),body:request.postDataJSON()});
  if(url.pathname==='/admin/fulfillment-holds')return route.fulfill({json:{items:[]}});
  if(url.pathname==='/admin/orders')return route.fulfill({json:{data:[digital,free],total:2,summary:{all:2,free:1,freeStarted:0,capturedCents:399}}});
  if(url.pathname==='/admin/pricing')return route.fulfill({json:{settings:{enabled:true,revision:2,markupPercent:30,feePercent:4,feeFixed:.3},prices:[{id:'de10',variantId:'',revision:2,checkedAt:now,priceCents:41099,landedCents:31014,shippingCents:1029,available:true}]}});
  if(url.pathname==='/free-downloads'){
   assert.equal(request.method(),'POST');assert.equal(request.postDataJSON().email,'sam@example.com');
   assert.equal(request.postDataJSON().newsletterConsent,true);
   return route.fulfill({json:{url:'https://downloads.test/free-download/'+ticket,orderReference:'RODDY-fixture',expiresAt:now+604800}});
  }
  if(url.pathname==='/admin/orders/paid-order/downloads'){
   assert.equal(request.method(),'POST');assert.equal(request.headers().authorization,'Bearer fixture');
   assert.equal(request.postDataJSON().productId,'desk');
   if(failDownload)return route.fulfill({status:409,json:{error:'Payment is not confirmed.'}});
   return route.fulfill({json:{name:'DESK COMMANDER',filename:'desk.zip',url:'https://downloads.test/download/'+ticket,expiresAt:now+(request.postDataJSON().purpose==='share'?604800:900)}});
  }
  if(url.pathname==='/download/'+ticket){
   assert.equal(request.headers().authorization,undefined,'Download tickets must not expose the GitHub credential');
   return route.fulfill({body:Buffer.from('fixture ZIP bytes'),contentType:'application/zip'});
  }
  throw new Error('Unexpected fixture request: '+url.pathname);
 });
 const base=`http://127.0.0.1:${server.httpServer.address().port}/__digital_downloads`;
 await page.goto(base);await page.getByRole('button',{name:'Download ZIP ↓',exact:true}).waitFor();
 const downloading=page.waitForEvent('download');await page.getByRole('button',{name:'Download ZIP ↓',exact:true}).click();assert.equal((await downloading).suggestedFilename(),'desk.zip');
 await page.getByRole('button',{name:'Create customer link',exact:true}).first().click();
 await page.getByLabel('Customer download link',{exact:true}).waitFor();
 assert.match(await page.getByRole('link',{name:'Open email draft ↗',exact:true}).getAttribute('href'),/^mailto:\?subject=/);
 await page.getByRole('button',{name:'Copy link ⧉',exact:true}).click();assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),'https://downloads.test/download/'+ticket);
 assert.ok(calls.some(c=>c.body?.purpose==='download'));assert.ok(calls.some(c=>c.body?.purpose==='share'));
 const freeCard=page.locator('.order-card').filter({hasText:'FREE GAME'});assert.match(await freeCard.innerText(),/sam@example.com/);assert.ok(await freeCard.getByRole('button',{name:'Write a thank-you ↗'}).isEnabled());
 await freeCard.getByRole('button',{name:'Write a thank-you ↗'}).click();assert.match(await page.getByLabel('Message',{exact:true}).inputValue(),/Thank you for downloading/);await page.getByRole('button',{name:'Close customer message'}).click();
 failDownload=true;await page.getByRole('button',{name:'Download ZIP ↓',exact:true}).click();await page.getByText('Payment is not confirmed.',{exact:true}).waitFor();
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Admin downloads must fit mobile');
 await page.goto(base+'?view=free');await page.getByRole('button',{name:'↓ Free game'}).click();
 assert.equal(await page.getByLabel(/I want occasional RODDY/).isChecked(),false,'Promotional opt-in must start unchecked');
 await page.getByRole('button',{name:'Get free download ↓'}).click();assert.equal(calls.filter(c=>c.path==='/free-downloads').length,0,'Blank email must not create an order');
 await page.getByLabel('Email address',{exact:true}).fill('sam@example.com');await page.getByLabel(/I want occasional RODDY/).check();await page.getByRole('button',{name:'Get free download ↓'}).click();
 await page.getByRole('link',{name:'Download now ↓'}).waitFor();assert.match(await page.getByRole('link',{name:'Download now ↓'}).getAttribute('href'),/\/free-download\/fixture-ticket$/);
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Free download dialog must fit mobile');
 await page.evaluate(()=>{window.fixtureProduct.id='another-game';});await page.getByRole('dialog').waitFor({state:'hidden'});
 await page.goto(base+'?view=price');await page.getByText('$410.99 + quoted shipping',{exact:true}).waitFor();assert.match(await page.locator('body').innerText(),/30% markup[\s\S]*\$310.14[\s\S]*\$10.29/);
 assert.deepEqual(errors,[]);
 console.log('PASS: admin ZIP download, refund rejection, copy/resend links, email drafts, free-order thank-you, required email, optional offers opt-in, mobile, and live DE10 pricing details. Fixture APIs only.');
}finally{await browser.close();await server.close();unlinkSync(entry);}
