import test from 'node:test';
import assert from 'node:assert/strict';
import {thankYouDraft,mailtoDraft,hasCurrentMessage} from './order-mail.js';
const order=()=>({id:'order-12345678',address:{first_name:'Sam',email:'sam@example.com'},messageContext:'current',messages:[],items:[{name:'RODDY keycaps',qty:2,supplier:{productUrl:'https://private-maker.example',supplierSku:'SECRET-SKU'},designSnapshot:{json:'SECRET-RECIPE'},procurement:{unitCostCents:1234}}],fulfillments:[{kind:'keycaps',supplierId:'SECRET-REFERENCE',state:'shipped',shipments:[{carrier:'UPS',number:'TRACK-123',url:'https://www.ups.com/track?number=TRACK-123'}]}]});
test('customer thank-you includes exact order and tracking while excluding every supplier field',()=>{
 const o=order(),d=thankYouDraft(o);assert.match(d.body,/Hi Sam/);assert.match(d.body,/2 × RODDY keycaps/);assert.match(d.body,/TRACK-123/);assert.match(d.body,/https:\/\/www.ups.com/);assert.match(d.subject,/#12345678/);
 for(const text of ['SECRET','private-maker','unitCostCents','keycaps.json','JSON'])assert.ok(!JSON.stringify(d).includes(text));
 const link=new URL(mailtoDraft(d));assert.equal(link.searchParams.get('subject'),d.subject);assert.equal(link.searchParams.get('body'),d.body);
});
test('partial shipments include every package and never claim the whole order shipped',()=>{
 const o=order();o.fulfillments.push({kind:'office',state:'ready-to-ship',shipments:[{carrier:'USPS',number:'OTHER',url:'javascript:alert(1)'}]});const d=thankYouDraft(o);
 assert.match(d.body,/Part of your order/);assert.match(d.body,/Package 2/);assert.match(d.body,/OTHER/);assert.match(d.body,/rest of your order/);assert.ok(!d.body.includes('javascript:'));
});
test('new physical and digital orders receive honest thank-yous without invented tracking',()=>{
 const o=order();o.fulfillments[0].state='awaiting-submission';o.fulfillments[0].shipments=[];assert.match(thankYouDraft(o).body,/when it ships/);assert.ok(!thankYouDraft(o).subject.includes('on its way'));
 o.fulfillments=[];assert.match(thankYouDraft(o).body,/digital items/);assert.ok(!thankYouDraft(o).body.includes('when it ships'));
});
test('mailto fields cannot inject recipients or headers; edited body stays intact',()=>{
 const d=thankYouDraft(order());for(const recipient of ['sam@example.com?bcc=other@example.com','sam@example.com\r\nBcc:x@example.com',''])assert.equal(mailtoDraft({...d,recipient}),'');
 assert.equal(mailtoDraft({...d,subject:'Hello\r\nBcc: other@example.com'}),'');
 const body='Thanks & enjoy!\nKeep this: ?bcc=nobody';assert.equal(new URL(mailtoDraft({...d,body})).searchParams.get('body'),body);
});
test('updated tracking requires a new sent confirmation, while prior messages stay in history',()=>{
 const o=order();o.messages=[{context:'previous',body:'Previous tracking'}];assert.equal(hasCurrentMessage(o),false);o.messages.push({context:'current'});assert.equal(hasCurrentMessage(o),true);assert.equal(o.messages.length,2);
});
