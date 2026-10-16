// Real components with fixture APIs; no live carts, orders or payments.
import {chromium} from '../.tools/node_modules/playwright/index.mjs';
import {createServer} from 'vite';
import assert from 'node:assert/strict';
import {writeFileSync,unlinkSync,mkdirSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
const entry='.tools/kits-'+randomUUID()+'.mjs';
writeFileSync(entry,`import {createApp,h} from 'vue';import {createPinia} from 'pinia';import {createRouter,createMemoryHistory} from 'vue-router';import KitCarts from '../src/admin/KitCarts.vue';import KitBomEditor from '../src/admin/KitBomEditor.vue';import Cart from '../src/views/Cart.vue';import Product from '../src/views/Product.vue';import ProductCard from '../src/components/ProductCard.vue';import {useCatalogStore} from '../src/stores/catalog';import {useCartStore} from '../src/stores/cart';import {normalizeProduct} from '../src/catalog-model';import '../src/styles/main.css';import '../src/admin/admin.css';
const pinia=createPinia(),router=createRouter({history:createMemoryHistory(),routes:[{path:'/',component:Cart}]});const catalog=useCatalogStore(pinia);catalog.loaded=true;catalog.settings.checkoutEndpoint='https://kits.test';catalog.settings.checkoutEnabled=true;catalog.products=[normalizeProduct({id:'kit',name:'Prototype kit',price:99.99,stock:0,active:true,status:'available',type:'physical',trackStock:false,fulfillment:'automatic',shippingCountries:['US'],prototypeWarning:'Testing has not been completed. Assembly and firmware work required.',supplier:{provider:'mouser',supplierSku:'kit-example',fulfillment:'automatic',bom:{revision:'H-v1',status:'ready',lines:[{supplierSku:'123-PART',quantity:2}]}}})];useCartStore(pinia).items=[{id:'kit',qty:2}];
const p=catalog.products[0],mode=new URLSearchParams(location.search).get('mode');if(!mode || mode==='editor')document.body.classList.add('admin-app');createApp({render:()=>mode==='cart'?h(Cart):mode==='product'?h(Product,{id:'kit'}):mode==='card'?h(ProductCard,{product:p}):mode==='editor'?h(KitBomEditor,{product:p}):h(KitCarts,{catalog,token:'fixture'})}).use(pinia).use(router).mount('#app');`);
const server=await createServer({optimizeDeps:{noDiscovery:true,include:['vue']},server:{host:'127.0.0.1',port:0},plugins:[{name:'kit-fixture',configureServer(server){server.middlewares.use('/__kit_test',(_req,res)=>{res.setHeader('Content-Type','text/html');res.end(`<html><meta name="viewport" content="width=device-width,initial-scale=1"><body><div id="app"></div><script type="module" src="/${entry}"></script></body></html>`);});}}]});
await server.listen();const browser=await chromium.launch({headless:true});
try {
 const page=await browser.newPage({viewport:{width:1200,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(15000);
 const carts=[];
 await page.route('https://kits.test/**',async route=>{
  assert.equal(new URL(route.request().url()).pathname,'/admin/kit-carts');
  if(route.request().method()==='POST'){
   assert.deepEqual(route.request().postDataJSON(),{productId:'kit',quantity:3,country:'US'});
   const cart={product:'kit',revision:'H-v1',quantity:3,country:'US',created:1792145869,cart:randomUUID()};carts.push(cart);await route.fulfill({json:{cart,message:'Fresh cart saved. No order was placed.'}});
  } else await route.fulfill({json:{carts}});
 });
 const url=`http://127.0.0.1:${server.httpServer.address().port}/__kit_test`;
 await page.goto(url);await page.getByLabel('Number of kits').fill('3');await page.getByRole('button',{name:'Build fresh cart'}).click();await page.getByText('Fresh cart saved. No order was placed.').waitFor();assert.equal(carts.length,1);
 await page.getByRole('button',{name:'Build fresh cart'}).click();await page.waitForFunction(()=>document.querySelectorAll('code').length===2);assert.notEqual(carts[0].cart,carts[1].cart);
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 for(const mode of ['card','product','cart']){
  await page.goto(url+'?mode='+mode);await page.getByText('TESTING NOT COMPLETE',{exact:true}).waitFor();
  const colors=await page.locator('.prototype-notice').evaluate(e=>({background:getComputedStyle(e).backgroundColor,text:getComputedStyle(e).color}));assert.deepEqual(colors,{background:'rgb(80, 25, 29)',text:'rgb(255, 243, 243)'});
  if(mode==='product')assert.ok(await page.getByRole('button',{name:'Add to cart +',exact:true}).isEnabled());
  if(mode==='cart')assert.ok(await page.getByRole('button',{name:'Update prices & shipping'}).isEnabled());
 }
 await page.goto(url+'?mode=editor');await page.getByLabel('Hardware / BOM revision').waitFor();await page.getByRole('button',{name:'Add part',exact:true}).click();assert.equal(await page.getByLabel('Mouser part number',{exact:true}).count(),2);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 assert.deepEqual(errors,[]);console.log('PASS kit components: fresh repeat carts, quantity, private reference history, mobile editor, red warnings on cards/product/cart, prototype purchase controls enabled. Fixture APIs only.');
}finally{await browser.close();await server.close();unlinkSync(entry);}
