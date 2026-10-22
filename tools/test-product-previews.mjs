// Test the built output as plain static hosting: no SPA fallback for public URLs.
// All checkout API traffic is intercepted. Never creates orders or sends mail.
import {createServer} from 'node:http';
import {readFile,stat,mkdir} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
import assert from 'node:assert/strict';
import {chromium} from '../.tools/node_modules/playwright/index.mjs';
import {publicProducts,productMetadata,productPath,STORE_ROUTES} from '../src/social-previews.js';
const root=resolve('dist'),catalog=JSON.parse(await readFile(root+'/data/products.json','utf8'));
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.ico':'image/x-icon'};
const server=createServer(async(req,res)=>{
 try{
  const url=new URL(req.url,'http://static.test'),path=resolve(root,'.'+decodeURIComponent(url.pathname));
  if(path!==root&&!path.startsWith(root+'/'))throw Error('Invalid path');
  let file=path,info=await stat(file);
  if(info.isDirectory()){
   if(!url.pathname.endsWith('/')){res.writeHead(301,{location:url.pathname+'/'+url.search});res.end();return;}
   file=resolve(file,'index.html');
  }
  const body=await readFile(file);res.writeHead(200,{'content-type':types[extname(file)]||'application/octet-stream'});res.end(body);
 }catch{res.writeHead(404,{'content-type':'text/html; charset=utf-8'});res.end(await readFile(root+'/404.html'));}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+server.address().port;
const browser=await chromium.launch(),context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage(),errors=[];
page.on('pageerror',e=>errors.push(e.message));await page.addInitScript(()=>localStorage.setItem('roddy:newsletter:joined','yes'));
await page.route('https://store-api.143-244-168-180.sslip.io/**',r=>r.fulfill({status:404,json:{error:'Fixture: no live API calls.'}}));
await page.route('**/inventory',r=>r.fulfill({json:{items:[],prices:[]}}));
try{
 for(const product of publicProducts(catalog)){
  for(const agent of ['facebookexternalhit/1.1','Discordbot/2.0']){
   const response=await fetch(base+productPath(product.id),{headers:{'user-agent':agent}});assert.equal(response.status,200);
   const html=await response.text(),metadata=productMetadata(product);
   assert.ok(html.includes(metadata.url));assert.ok(html.includes(metadata.image));
   assert.equal((html.match(/property="og:image"/g)||[]).length,1);
   const image=html.match(/property="og:image" content="([^"]+)"/)[1];assert.match(image,/\?v=[a-f0-9]{12}$/);
   const file=await fetch(base+new URL(image).pathname+new URL(image).search);assert.equal(file.status,200);assert.match(file.headers.get('content-type'),/^image\//);
  }
 }
 const noJS=await browser.newContext({javaScriptEnabled:false}),crawler=await noJS.newPage();await crawler.goto(base+'/product/buddy/');assert.match(await crawler.title(),/^BUDDY/);assert.match(await crawler.locator('noscript').innerText(),/BUDDY/);await noJS.close();
 await page.goto(base+'/product/buddy/');await page.locator('h1').filter({hasText:'BUDDY'}).waitFor();await page.reload();await page.locator('.buddy-centered').waitFor();
 await page.getByRole('link',{name:'← Back to the store'}).click();await page.locator('.shop-directory').waitFor();assert.equal(new URL(page.url()).hash,'');
 await page.locator('.product-card').filter({hasText:'ORBIT'}).click();await page.locator('h1').filter({hasText:'ORBIT'}).waitFor();assert.match(await page.title(),/^ORBIT/);assert.match(await page.locator('meta[property="og:image"]').getAttribute('content'),/orbit\/lounge/);
 await page.goBack();await page.locator('.shop-directory').waitFor();await page.goForward();await page.locator('h1').filter({hasText:'ORBIT'}).waitFor();
 for(const url of ['/#/product/buddy','/index.html#/product/buddy']){await page.goto(base+url);await page.locator('.buddy-centered').waitFor();assert.equal(new URL(page.url()).pathname,'/product/buddy');assert.equal(new URL(page.url()).hash,'');}
 await page.goto(base+'/');await page.locator('.world-hero').waitFor();await page.goto(base+'/#/product/buddy');await page.locator('.buddy-centered').waitFor();assert.equal(new URL(page.url()).hash,'');
 await page.goto(base+'/product/desk-commander/');await page.getByRole('button',{name:'Add to cart +',exact:true}).click();await page.goto(base+'/cart/');await page.getByRole('heading',{name:'YOUR CART.'}).waitFor();assert.ok((await page.locator('main').textContent()).includes('DESK COMMANDER'));await page.reload();assert.ok((await page.locator('main').textContent()).includes('DESK COMMANDER'));
 for(const route of STORE_ROUTES){const response=await page.goto(base+'/'+route+'/');assert.equal(response.status(),200);await page.locator('main').waitFor();}
 const hidden=catalog.categories.find(c=>c.visible===false),secret=hidden.previewKey,hiddenProduct=catalog.products.find(p=>p.active&&p.category===hidden.id);
 assert.equal((await fetch(base+productPath(hiddenProduct.id))).status,404);
 await page.goto(base+'/?category-preview='+secret+'#/shop?cat='+hidden.id);await page.locator('.preview-notice').waitFor({state:'hidden'});await page.locator('.shop-directory').waitFor();await page.locator('.product-card').first().click();await page.locator('h1').waitFor();assert.equal(new URL(page.url()).searchParams.get('category-preview'),secret);await page.reload();await page.locator('h1').waitFor();assert.ok(await page.locator('meta[data-unlisted-robots]').count());
 await page.goto(base+'/index.html?preview=1#/product/buddy');await page.locator('.buddy-centered').waitFor();await page.getByRole('link',{name:'← Back to the store'}).click();assert.equal(new URL(page.url()).searchParams.get('preview'),'1');
 await page.setViewportSize({width:390,height:844});await page.goto(base+'/product/buddy/');await page.locator('.buddy-centered').waitFor();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 assert.deepEqual(errors,[]);await mkdir('.tools/product-previews',{recursive:true});await page.screenshot({path:'.tools/product-previews/clean-product-phone.png'});
 console.log('PASS: '+publicProducts(catalog).length+' crawler-readable product previews and images, no-JavaScript HTML, direct links, refresh/back/forward, old bookmarks, cart persistence, static store routes, unlisted/draft previews and phone layout.');
}finally{await context.close();await browser.close();await new Promise(r=>server.close(r));}
