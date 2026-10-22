import test from 'node:test';
import assert from 'node:assert/strict';
import {legacyStoreTarget} from './legacy-links.js';

test('old product links upgrade while preserving preview context and query parameters',()=>{
 assert.equal(legacyStoreTarget('https://roddy.world/#/product/buddy'),'/product/buddy');
 assert.equal(legacyStoreTarget('https://roddy.world/index.html?preview=1#/product/buddy'),'/product/buddy?preview=1');
 assert.equal(legacyStoreTarget('https://roddy.world/?category-preview=secret#/shop?cat=kits'),'/shop?cat=kits&category-preview=secret');
 assert.equal(legacyStoreTarget('https://roddy.world/index.html'),'/');
 assert.equal(legacyStoreTarget('https://roddy.world/#/product/buddy?x=1&x=2'),'/product/buddy?x=1&x=2');
});
test('receipts, admin paths, existing clean URLs and external-looking hashes are left alone',()=>{
 for(const path of ['/order.html#session_id=private','/admin.html#workshop','/product/buddy/','/about/','/#//evil.example/path','/#/\\evil.example/path'])assert.equal(legacyStoreTarget('https://roddy.world'+path),null,path);
});
