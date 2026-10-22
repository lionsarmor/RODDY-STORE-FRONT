// Local browser fixtures: no real orders, accounts, mail or supplier calls.
import {createServer} from 'vite';
import {mkdirSync} from 'node:fs';
import {chromium} from '../.tools/node_modules/playwright/index.mjs';
import assert from 'node:assert/strict';
mkdirSync('.tools/alpha-store',{recursive:true});
const server=await createServer({server:{host:'127.0.0.1',port:0}});await server.listen();
const base='http://127.0.0.1:'+server.httpServer.address().port;
const browser=await chromium.launch(),page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],requests=[];
await page.addInitScript(()=>localStorage.setItem('roddy:newsletter:joined','yes'));
page.on('pageerror',e=>errors.push(e.message));
await page.route('https://store-api.143-244-168-180.sslip.io/**',r=>r.fulfill({status:404,json:{error:'No live API in fixture tests.'}}));
await page.route('**/inventory',r=>r.fulfill({json:{items:[],prices:[]}}));
await page.route('**/free-downloads',async r=>{const body=r.request().postDataJSON();requests.push(body);await r.fulfill(body.testerCode==='TEST-RETRO-CODE'?{json:{url:'https://store-api.143-244-168-180.sslip.io/free-download/'+'A'.repeat(43),orderReference:'RODDY-test',expiresAt:Date.now()/1000+604800}}:{status:403,json:{error:'That tester code did not unlock this alpha. Ask in the RODDY Discord for access.'}});});
try{
 await page.goto(base+'/#/product/buddy');await page.locator('h1').filter({hasText:'BUDDY'}).waitFor();
 assert.equal(await page.locator('.software-edition').count(),7);assert.equal(await page.locator('.software-launch select').count(),0);
 await page.screenshot({path:'.tools/alpha-store/buddy-desktop.png',fullPage:true});
 const card=page.locator('.software-edition').filter({hasText:'BUDDY · DOS'});await card.getByRole('button',{name:'Unlock this alpha'}).click();
 const dialog=page.getByRole('dialog',{name:'Free download: BUDDY'});assert.equal(await dialog.locator('input[type=checkbox]').isChecked(),false);assert.equal(await dialog.locator('input[type=password]').count(),1);
 await dialog.getByLabel('Email address').fill('fixture@example.com');await dialog.getByLabel('Beta tester code').fill('NOPE');await dialog.getByRole('button',{name:'Unlock alpha download'}).click();await dialog.getByRole('alert').waitFor();assert.match(await dialog.getByRole('alert').textContent(),/tester code/);assert.equal(await dialog.getByRole('link',{name:'Download now'}).count(),0);
 await dialog.getByLabel('Beta tester code').fill('TEST-RETRO-CODE');await dialog.getByRole('button',{name:'Unlock alpha download'}).click();await dialog.getByRole('link',{name:'Download now'}).waitFor();assert.equal(requests.at(-1).editionId,'dos');assert.equal(requests.at(-1).newsletterConsent,false);assert.equal(await dialog.locator('input[type=password]').count(),0);
 await page.goto(base+'/#/product/orbit');await page.locator('h1').filter({hasText:'ORBIT'}).waitFor();assert.equal(await page.locator('dialog[open]').count(),0);assert.equal(await page.locator('.software-edition').count(),1);assert.equal(await page.locator('.software-screen-grid figure').count(),6);
 await page.screenshot({path:'.tools/alpha-store/orbit-desktop.png',fullPage:true});
 await page.locator('.hero-screen button').click();await page.getByRole('button',{name:'Close screenshot'}).waitFor();await page.keyboard.press('Escape');
 for(const name of ['buddy','orbit']){await page.setViewportSize({width:390,height:844});await page.goto(base+'/#/product/'+name);await page.locator('h1').filter({hasText:name.toUpperCase()}).waitFor();await page.waitForTimeout(200);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'No mobile horizontal overflow');await page.screenshot({path:'.tools/alpha-store/'+name+'-phone.png',fullPage:true});await page.locator('.software-edition').first().getByRole('button',{name:'Unlock this alpha'}).click();await page.screenshot({path:'.tools/alpha-store/'+name+'-gate-phone.png'});await page.keyboard.press('Escape');}
 await page.goto(base+'/#/');await page.locator('.promo-grid').waitFor();assert.equal(await page.locator('.promo-grid .promo-ad').count(),2);assert.ok(await page.locator('a[href="https://discord.gg/YVKJ5srkj"]').count()>=2);
 await page.goto(base+'/#/product/keychain-kreatures');await page.locator('.coming-soon-panel').waitFor();assert.ok(await page.locator('a[href="https://discord.gg/YVKJ5srkj"]').count()>=2);
 assert.deepEqual(errors,[]);console.log('PASS: seven edition cards, ORBIT gallery, code/email gate, denied and valid requests, edition selection, route resets, lightbox, Discord promotion and mobile layout.');
}finally{await browser.close();await server.close();}
