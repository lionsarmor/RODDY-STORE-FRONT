export function publicCatalog(catalog,references={}) {
 const out=JSON.parse(JSON.stringify(catalog));
 for(const p of out.products){
  p.githubUrl=''; // Repository links are private; never restore them from an older admin draft.
  if(p.specs)p.specs=Object.fromEntries(Object.entries(p.specs).filter(([key])=>!/supplier|print provider|fulfillment/i.test(key)));
  if(references[p.id])p.fulfillmentRef=references[p.id];
  if(p.supplier){p.fulfillment=p.supplier.fulfillment;p.supplier=null;}
  if(p.merch?.provider==='printify'){
   const m=p.merch;p.merch={provider:'custom',shippingCountries:m.shippingCountries,shippingWarning:'',
    variants:m.variants.map(v=>Object.fromEntries(['id','size','color','colors','price','enabled','available','image'].filter(k=>k in v).map(k=>[k,v[k]]))),
    shippingProfiles:(m.shippingProfiles || []).map(r=>({...r,variantIds:r.variantIds.map(String)}))};
  }
 }
 return out;
}
export function hydrateCatalog(catalog,sources={}) {
 const out=JSON.parse(JSON.stringify(catalog));
 for(const p of out.products){
  if(!p.fulfillmentRef)continue;
  const source=sources[p.id]?.[p.fulfillmentRef];
  if(!source)throw new Error('A private product mapping could not load. Reload the admin connection before publishing.');
  if(source.supplier)p.supplier=JSON.parse(JSON.stringify(source.supplier));
  if(source.merch){const m=JSON.parse(JSON.stringify(source.merch)),pub=p.merch;
   m.variants=pub.variants.map(v=>({...m.variants.find(x=>x.id===v.id),...v}));
   for(const k of ['shippingCountries','shippingProfiles','shippingWarning'])if(k in pub)m[k]=pub[k];
   p.merch=m;
  }
 }
 return out;
}
