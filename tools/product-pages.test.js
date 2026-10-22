import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {publicProducts,productMetadata,previewHtml,productPath,STORE_IMAGE} from '../src/social-previews.js';
const catalog=JSON.parse(readFileSync(new URL('../public/data/products.json',import.meta.url)));
const template=readFileSync(new URL('../index.html',import.meta.url),'utf8');

test('every public product gets its own image, canonical URL and metadata in crawler HTML',()=>{
 const products=publicProducts(catalog);assert.ok(products.length>=16);
 for(const product of products){
  const metadata=productMetadata(product),html=previewHtml(template,metadata,{product:true});
  assert.equal(metadata.url,'https://roddy.world/product/'+product.id+'/');
  assert.notEqual(metadata.image,STORE_IMAGE,product.id+' needs an actual product image');
  assert.ok(existsSync(new URL('../public/'+new URL(metadata.image).pathname.slice(1),import.meta.url)),product.id);
  assert.equal((html.match(/property="og:image"/g)||[]).length,1);
  assert.equal((html.match(/name="twitter:image"/g)||[]).length,1);
  assert.ok(html.includes('<noscript>'));assert.ok(html.includes(metadata.image));
  assert.ok(!html.includes('og:image:width'));assert.ok(!html.includes('og:image:height'));
 }
});
test('inactive and unlisted catalog entries never get public preview pages',()=>{
 const ids=new Set(publicProducts(catalog).map(p=>p.id));
 for(const p of catalog.products){const category=catalog.categories.find(c=>c.id===p.category);if(!p.active||category?.visible===false)assert.ok(!ids.has(p.id));}
});
test('catalog text is escaped and unsupported image URLs cannot become preview assets',()=>{
 const metadata=productMetadata({id:'test',name:'A "special" <game>',shortDescription:'One & two "three" <script>bad</script>',cardImage:'javascript:alert(1)',coverImage:'https://user:pass@example.com/img.png',images:['img/buddy/login-night-shift.png']});
 const html=previewHtml(template,metadata,{product:true});assert.ok(html.includes('A &quot;special&quot; &lt;game&gt;'));assert.ok(!html.includes('<script>bad'));
 assert.ok(metadata.image.endsWith('/img/buddy/login-night-shift.png'));
 assert.ok(!html.includes('javascript:'));assert.throws(()=>productPath('../secret'));
 assert.equal(productMetadata({id:'no-image',name:'No image',images:['data:image/png;base64,SECRET']}).image,STORE_IMAGE);
});
test('a dedicated social photograph takes priority without changing the storefront cover',()=>{
 const product={id:'buddy',name:'BUDDY',coverImage:'img/buddy/x16-1.png',socialImage:'img/buddy/login-night-shift.png'};
 assert.ok(productMetadata(product).image.endsWith('/img/buddy/login-night-shift.png'));
 assert.equal(product.coverImage,'img/buddy/x16-1.png');
});
