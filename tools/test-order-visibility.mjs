// Browser regression for the actual order component. All orders and APIs are fixtures.
// Requires Playwright in .tools/node_modules (as used by the customer-guide builder).
import {chromium} from '../.tools/node_modules/playwright/index.mjs';
import {createServer} from 'vite';
import assert from 'node:assert/strict';
import {writeFileSync,unlinkSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
const entry='.tools/order-visibility-'+randomUUID()+'.mjs';
writeFileSync(entry,`import {createApp,h} from 'vue';
import OrderManager from '../src/admin/OrderManager.vue';
import '../src/styles/main.css';
import '../src/admin/admin.css';
window.testApp=createApp({render:()=>h(OrderManager,{endpoint:'https://orders.test',token:'fixture',connected:true})});
window.testApp.mount('#app');`);
const server=await createServer({optimizeDeps:{noDiscovery:true,include:['vue']},server:{host:'127.0.0.1',port:0},plugins:[{name:'order-visibility-fixture',configureServer(server){
 server.middlewares.use('/__order_visibility_test',(_req,res)=>{
  res.setHeader('Content-Type','text/html');
  res.end(`<html><body><div id="app"></div><script type="module" src="/${entry}"></script></body></html>`);
 });
}}]});
await server.listen();
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],requests=[];
page.on('pageerror',e=>{errors.push(e.message);console.error(e.message);});
page.setDefaultTimeout(15000);
let state='in-production';
const order=(id,kind='printify')=>({id,created:1792135383,amount_total:4518,payment_status:'paid',items:[{name:kind==='digital'?'DIGITAL APP':'TEST HOODIE',kind,qty:1}],fulfillments:kind==='digital'?[]:[{kind,state,supplierId:'fixture-supplier-order',updated:1792135400,shipments:[]}],finance:{captured:4518},expenses:[],messages:[],orderPacket:{}});
try{
 await page.route('https://orders.test/**',async route=>{
  assert.equal(route.request().method(),'GET','Browser test must never purchase, submit or modify an order');
  const url=new URL(route.request().url());requests.push(url.searchParams.toString());
  const all=url.searchParams.get('view')==='all',progress=url.searchParams.get('view')==='progress';
  const second=url.searchParams.has('cursor');
  const data=all?(second?[order('older-order')]:[order('automated-hoodie'),order('digital-sale','digital'),...Array.from({length:48},(_,i)=>order('order-'+i))]):progress?[order('automated-hoodie')]:[];
  await route.fulfill({json:{data,total:all?51:progress?1:0,next_cursor:all&&!second?'page-two':'',summary:{all:51,inbox:0,progress:1,shipped:0,capturedCents:4518}}});
 });
 await page.clock.install();
 await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__order_visibility_test`);
 await page.locator('.order-card').first().waitFor();
 assert.equal(new URLSearchParams(requests[0]).get('view'),'all');
 assert.equal(await page.locator('.order-card').count(),50);
 assert.match(await page.locator('.order-card').first().innerText(),/TEST HOODIE[\s\S]*in production[\s\S]*Automatic fulfillment[\s\S]*fixture-supplier-order/i);
 await page.getByRole('button',{name:'Load more orders'}).click();
 await page.waitForFunction(()=>document.querySelectorAll('.order-card').length===51);
 state='shipped';await page.clock.runFor(30001);
 await page.waitForFunction(()=>document.querySelector('.step-chip')?.textContent==='Shipped');
 assert.equal(await page.locator('.order-card').count(),51,'Background refresh must preserve loaded history');
 await page.getByRole('button',{name:/Needs your action/}).click();
 await page.getByRole('heading',{name:'No manual actions waiting.'}).waitFor();
 assert.match(await page.locator('.order-empty').innerText(),/Automated orders remain visible/);
 await page.getByRole('button',{name:'Show all orders',exact:true}).click();
 await page.locator('.order-card').first().waitFor();
 assert.equal(new URLSearchParams(requests.at(-1)).get('view'),'all');
 await page.setViewportSize({width:390,height:844});
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Order desk must fit mobile');
 const count=requests.length;
 await page.evaluate(()=>window.testApp.unmount());await page.clock.runFor(60001);
 assert.equal(requests.length,count,'Unmount must stop automatic refresh');
 assert.deepEqual(errors,[]);
 console.log('PASS: all orders open by default; automatic and digital orders visible; status refresh preserves pagination; empty action queue explains automated orders; clear filters; mobile; timer cleanup.');
}finally{await browser.close();await server.close();unlinkSync(entry);}
