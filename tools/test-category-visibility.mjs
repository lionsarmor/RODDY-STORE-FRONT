// Public browsing plus real admin controls in an isolated browser. No publication,
// supplier cart, purchase, payment or admin authentication is performed.
import {chromium} from '../.tools/node_modules/playwright/index.mjs';
import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const data=JSON.parse(readFileSync('public/data/products.json'));
const base=process.env.CHECK_BASE || 'http://127.0.0.1:5183/';
const kits=data.products.filter(p=>p.category==='kits');
const category=data.categories.find(c=>c.id==='kits');
const browser=await chromium.launch({headless:true});
try{
 const context=await browser.newContext({viewport:{width:1440,height:1000}});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 if(!process.env.CHECK_BASE)await page.route('**/inventory',r=>r.fulfill({json:{}}));
 const go=async hash=>{await page.goto(base+hash);await page.locator('nav[aria-label="Main navigation"]').waitFor();};
 await go('#/shop');await page.locator('.product-card').first().waitFor();
 assert.deepEqual(await page.locator('nav[aria-label="Main navigation"] a').allTextContents(),['Home','Shop','About','Contact']);
 assert.equal(await page.locator('nav[aria-label="Shop departments"] a[href*="cat=kits"]').count(),0);
 for(const kit of kits)assert.equal(await page.locator('a[href="#/product/'+kit.id+'"]').count(),0);
 await go('#/');await page.locator('.world-hero').waitFor();
 for(const kit of kits)assert.equal(await page.locator('a[href="#/product/'+kit.id+'"]').count(),0);
 await go('#/shop?cat=kits');await page.getByText('Page not found.',{exact:false}).waitFor();
 for(const kit of kits){await go('#/product/'+kit.id);await page.getByText('not found',{exact:false}).first().waitFor();assert.equal(await page.locator('.image-expand').count(),0);}
 await go('?category-preview=wrong-link#/shop?cat=kits');await page.getByText('Page not found.',{exact:false}).waitFor();
 const previewBase=base+'?category-preview='+category.previewKey;
 await page.goto(previewBase+'#/shop?cat=kits');await page.locator('.product-card').first().waitFor();assert.equal(await page.locator('.product-card').count(),kits.length);
 assert.equal(await page.locator('meta[name="robots"][content="noindex, nofollow"]').count(),1);
 await page.locator('a.product-card[href="#/product/'+kits[0].id+'"]').click();await page.locator('.image-expand img').first().waitFor();assert.equal(new URL(page.url()).searchParams.get('category-preview'),category.previewKey);
 for(const kit of kits){await page.goto(previewBase+'#/product/'+kit.id);const img=page.locator('.image-expand img').first();await img.waitFor();await img.evaluate(e=>e.decode());assert.ok(await img.evaluate(e=>e.naturalWidth>0));const parent=kit.id.startsWith('keychain')?'keychain-kreatures':'link-commander-e';assert.ok(await page.locator('a[href="#/product/'+parent+'"]').count()>0);}
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.getByRole('link',{name:'Return to public store'}).click();assert.equal(new URL(page.url()).search,'');await page.locator('.world-hero').waitFor();assert.equal(await page.getByText('Unlisted preview:',{exact:false}).count(),0);
 // Exercise actual admin in local mode only; live check remains read-only.
 if(!process.env.CHECK_BASE){
  const admin=await context.newPage();admin.on('pageerror',e=>errors.push(e.message));
  await context.grantPermissions(['clipboard-read','clipboard-write'],{origin:new URL(base).origin});
  await admin.goto(base+'admin.html');await admin.getByRole('button',{name:'Categories',exact:false}).first().click();
  const row=admin.locator('section[aria-label="Kits category"]');await row.waitFor();const toggle=row.getByRole('checkbox');assert.equal(await toggle.isChecked(),false);
  const oldLink=await row.getByLabel('Unlisted preview link').inputValue();assert.equal(new URL(oldLink).searchParams.get('category-preview'),category.previewKey);
  await row.getByRole('button',{name:'Copy preview link',exact:true}).click();assert.equal(await admin.evaluate(()=>navigator.clipboard.readText()),oldLink);
  await toggle.check();assert.equal(await row.getByLabel('Unlisted preview link').count(),0);await toggle.uncheck();assert.equal(await row.getByLabel('Unlisted preview link').inputValue(),oldLink);
  await row.getByRole('button',{name:'Reset preview link'}).click();assert.notEqual(await row.getByLabel('Unlisted preview link').inputValue(),oldLink);
  await row.getByRole('button',{name:'Delete',exact:true}).click();await admin.getByRole('alert').filter({hasText:'Move this category'}).waitFor();assert.equal(await row.count(),1);
  await admin.getByRole('button',{name:'Add category +',exact:true}).click();const added=admin.locator('section[aria-label="New category category"]');await added.getByLabel('Name',{exact:true}).fill('Workshop');
  const workshop=admin.locator('section[aria-label="Workshop category"]');await workshop.getByLabel('ID',{exact:true}).fill('workshop');await workshop.getByLabel('ID',{exact:true}).press('Tab');assert.equal(await workshop.getByRole('checkbox').isChecked(),false);
  await workshop.getByRole('checkbox').check();await admin.waitForFunction(()=>Object.keys(localStorage).filter(k=>k.startsWith('roddy:admin:draft:')).some(k=>JSON.parse(localStorage[k]).catalog.categories.some(c=>c.id==='workshop'&&c.visible===true)));
  await admin.setViewportSize({width:390,height:844});assert.ok(await admin.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await admin.screenshot({path:'.tools/full-kit-audit/category-admin-mobile.png',fullPage:true});
 }
 assert.deepEqual(errors,[]);console.log('PASS category visibility: hidden public lists/direct URLs, valid scoped preview, navigation persistence, original-product links, mobile, '+(!process.env.CHECK_BASE?'admin create/toggle/copy/reset/delete guard/draft persistence':'live public and preview paths')+'.');
}finally{await browser.close()}
