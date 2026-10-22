// Run after Vite: social crawlers need product metadata in the HTTP response.
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {SITE_URL,STORE_TITLE,STORE_DESCRIPTION,STORE_IMAGE,STORE_ROUTES,publicProducts,productPath,productMetadata,previewHtml} from '../src/social-previews.js';
const dist=resolve('dist'),catalog=JSON.parse(await readFile('public/data/products.json','utf8'));
const template=await readFile(resolve(dist,'index.html'),'utf8');
if (!template.includes('src="/assets/')) throw new Error('Nested pages require root-relative Vite assets.');
const store={title:STORE_TITLE,description:STORE_DESCRIPTION,image:STORE_IMAGE,imageAlt:'RODDY logo — Play. Build. Make it yours.',url:SITE_URL+'/'};
await writeFile(resolve(dist,'index.html'),previewHtml(template,store));
for(const route of STORE_ROUTES){
  await mkdir(resolve(dist,route),{recursive:true});
  const privateRoute=['cart','account'].includes(route);
  await writeFile(resolve(dist,route,'index.html'),previewHtml(template,{...store,url:SITE_URL+'/'+route+'/'},{noindex:privateRoute}));
}
const products=publicProducts(catalog);
for(const product of products){
  const path=productPath(product.id),directory=resolve(dist,'.'+path);
  await mkdir(directory,{recursive:true});
  const metadata=productMetadata(product),image=new URL(metadata.image);
  if(image.origin===SITE_URL){
    const content=await readFile(resolve(dist,'.'+decodeURIComponent(image.pathname)));
    image.searchParams.set('v',createHash('sha256').update(content).digest('hex').slice(0,12));
    metadata.image=image.href;
  }
  await writeFile(resolve(directory,'index.html'),previewHtml(template,metadata,{product:true}));
}
await writeFile(resolve(dist,'404.html'),previewHtml(template,store,{noindex:true}));
const locations=[SITE_URL+'/',SITE_URL+'/shop/',...products.map(p=>SITE_URL+productPath(p.id))];
await writeFile(resolve(dist,'sitemap.xml'),'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+locations.map(url=>'  <url><loc>'+url+'</loc></url>').join('\n')+'\n</urlset>\n');
console.log('Generated '+products.length+' product pages with static social previews, store routes and sitemap.');
