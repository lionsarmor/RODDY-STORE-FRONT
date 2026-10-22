import {visibleProducts} from './category-visibility.js';

export const SITE_URL = 'https://roddy.world';
export const STORE_TITLE = 'RODDY — Play. Build. Make it yours.';
export const STORE_DESCRIPTION = 'RODDY: physical games, computers, electronic toys and programmable machines. Play it. Open it. Program it. Keep it.';
export const STORE_IMAGE = SITE_URL + '/social-card-roddy-20261014.png';
export const STORE_ROUTES = ['shop', 'cart', 'account', 'about', 'contact', 'newsletter'];
export const publicProducts = catalog => visibleProducts(catalog.products, catalog.categories);
export const escapeHtml = value => String(value).replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
export function productPath(id) {
  if (!/^[a-z0-9][a-z0-9-]*$/.test(id)) throw new Error('Invalid product ID for a public page.');
  return '/product/' + id + '/';
}
export function productImage(product) {
  for (const value of [product.socialImage, product.cardImage, product.coverImage, ...(product.images || []), product.image]) {
    if (!value || typeof value !== 'string') continue;
    try {
      const url = new URL(value, SITE_URL + '/');
      if (url.protocol !== 'https:' || url.username || url.password || !/\.(png|jpe?g|webp|gif)$/i.test(url.pathname)) continue;
      if (!/^(https:\/\/|img\/)/.test(value) || value.split('/').includes('..')) continue;
      return url.href;
    } catch { /* Try the next product photograph. */ }
  }
  return STORE_IMAGE;
}
export function productMetadata(product) {
  return {
    title: product.name + ' · RODDY',
    description: String(product.shortDescription || product.description || product.name).replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim().slice(0, 300),
    image: productImage(product), imageAlt: product.name + ' — product preview',
    url: SITE_URL + productPath(product.id),
  };
}
export function previewHtml(template, metadata, {noindex=false, product=false}={}) {
  // Remove the generic card before adding exactly one definitive preview.
  const head = template.replace(/<title>[^]*?<\/title>\s*/i, '')
    .replace(/<meta\s+(?:name|property)=["'](?:description|og:[^"']+|twitter:[^"']+|robots)["'][^>]*>\s*/gi, '')
    .replace(/<link\s+rel=["'](?:canonical|image_src)["'][^>]*>\s*/gi, '');
  const attr = escapeHtml, tags = [
    `<title>${attr(metadata.title)}</title>`,
    `<meta name="description" content="${attr(metadata.description)}">`,
    `<link rel="canonical" href="${attr(metadata.url)}">`,
    '<meta property="og:type" content="website">',
    '<meta property="og:site_name" content="RODDY">',
    `<meta property="og:url" content="${attr(metadata.url)}">`,
    `<meta property="og:title" content="${attr(metadata.title)}">`,
    `<meta property="og:description" content="${attr(metadata.description)}">`,
    `<meta property="og:image" content="${attr(metadata.image)}">`,
    `<meta property="og:image:secure_url" content="${attr(metadata.image)}">`,
    `<meta property="og:image:alt" content="${attr(metadata.imageAlt)}">`,
    '<meta name="twitter:card" content="summary_large_image">',
    `<meta name="twitter:title" content="${attr(metadata.title)}">`,
    `<meta name="twitter:description" content="${attr(metadata.description)}">`,
    `<meta name="twitter:image" content="${attr(metadata.image)}">`,
    `<meta name="twitter:image:alt" content="${attr(metadata.imageAlt)}">`,
    `<link rel="image_src" href="${attr(metadata.image)}">`,
  ];
  if (noindex) tags.push('<meta name="robots" content="noindex, nofollow">');
  let result = head.replace('</head>', tags.join('\n') + '\n</head>');
  if (product) result = result.replace('<div id="app"></div>', `<div id="app"></div>\n<noscript><h1>${attr(metadata.title)}</h1><p>${attr(metadata.description)}</p><p>Enable JavaScript to customize this item or order from the store.</p><a href="/shop/">Browse the store</a></noscript>`);
  return result;
}

export function updatePreviewMetadata(document, metadata, noindex=false) {
  document.title=metadata.title;
  function meta(kind,key,value) {
    let tag=document.head.querySelector(`meta[${kind}="${key}"]`);
    if(!tag){tag=document.createElement('meta');tag.setAttribute(kind,key);document.head.appendChild(tag);}
    tag.content=value;
  }
  meta('name','description',metadata.description);
  for(const [key,value] of Object.entries({type:'website',site_name:'RODDY',url:metadata.url,title:metadata.title,description:metadata.description,image:metadata.image,'image:secure_url':metadata.image,'image:alt':metadata.imageAlt}))meta('property','og:'+key,value);
  for(const [key,value] of Object.entries({card:'summary_large_image',title:metadata.title,description:metadata.description,image:metadata.image,'image:alt':metadata.imageAlt}))meta('name','twitter:'+key,value);
  for(const rel of ['canonical','image_src']){
    let link=document.head.querySelector(`link[rel="${rel}"]`);
    if(!link){link=document.createElement('link');link.rel=rel;document.head.appendChild(link);}
    link.href=rel==='canonical'?metadata.url:metadata.image;
  }
  document.head.querySelectorAll('meta[property="og:image:width"],meta[property="og:image:height"],meta[name="robots"]:not([data-unlisted-robots])').forEach(tag=>tag.remove());
  if(noindex)meta('name','robots','noindex, nofollow');
}
