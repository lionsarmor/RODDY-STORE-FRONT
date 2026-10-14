"""Versioned supplier mappings kept off the public product catalog."""
import base64,copy,hashlib,json,os
from pathlib import Path
import re,secrets,threading
from fastapi import HTTPException,Request
import httpx
from urllib.parse import urlsplit

class CatalogSourcing:
 def __init__(self,path):self.path=Path(path);self.lock=threading.RLock()
 def read(self):
  try:return json.loads(self.path.read_text())
  except FileNotFoundError:return {'products':{}}
 def save(self,products):
  if not isinstance(products,list) or len(products)>1000:raise HTTPException(400,'Check the product mappings.')
  references={}
  with self.lock:
   data=self.read()
   for p in products:
    if not isinstance(p,dict):raise HTTPException(400,'Check the product mappings.')
    ident=p.get('id','')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,150}',ident):raise HTTPException(400,'Check product IDs.')
    source={k:p[k] for k in ['supplier','merch'] if p.get(k)}
    if not source:continue
    if source.get('supplier') and source['supplier'].get('provider') not in {'aliexpress','mouser'}:raise HTTPException(400,'Unsupported supplier mapping.')
    if source.get('merch') and source['merch'].get('provider')!='printify':raise HTTPException(400,'Unsupported merchandise mapping.')
    encoded=json.dumps(source,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode();reference=hashlib.sha256(encoded).hexdigest()
    data['products'].setdefault(ident,{})[reference]=source;references[ident]=reference
   self.path.parent.mkdir(parents=True,exist_ok=True);temporary=self.path.with_name('.sourcing-'+secrets.token_hex(16))
   try:
    with open(temporary,'x') as f:os.chmod(temporary,0o600);json.dump(data,f);f.flush();os.fsync(f.fileno())
    os.replace(temporary,self.path)
   finally:temporary.unlink(missing_ok=True)
  return references
 def hydrate(self,catalog):
  catalog=copy.deepcopy(catalog);data=self.read()['products']
  for p in catalog.get('products',[]):
   if not p.get('fulfillmentRef'):continue
   source=data.get(p['id'],{}).get(p['fulfillmentRef'])
   if not source:raise HTTPException(503,'A product configuration is temporarily unavailable.')
   if source.get('supplier'):p['supplier']=copy.deepcopy(source['supplier'])
   if source.get('merch'):
    public=p.get('merch') or {};private=copy.deepcopy(source['merch']);variants={v['id']:v for v in private['variants']}
    private['variants']=[{**variants[v['id']],**v,'providerVariantId':variants[v['id']]['providerVariantId']} for v in public.get('variants',[]) if v['id'] in variants]
    for field in ['shippingCountries','shippingProfiles','shippingWarning']:
     if field in public:private[field]=public[field]
    p['merch']=private
  return catalog

def public_catalog(catalog,references):
 result=copy.deepcopy(catalog)
 for p in result.get('products',[]):
  if p.get('specs'):p['specs']={k:v for k,v in p['specs'].items() if not re.search('supplier|print provider|fulfillment',k,re.I)}
  if p['id'] in references:p['fulfillmentRef']=references[p['id']]
  if p.get('supplier'):p['fulfillment']=p['supplier']['fulfillment'];p['supplier']=None
  if p.get('merch') and p['merch'].get('provider')=='printify':
   m=p['merch'];p['merch']={k:m[k] for k in ['shippingCountries','shippingWarning'] if k in m};p['merch']['provider']='custom';p['merch']['shippingWarning']=''
   p['merch']['variants']=[{k:v[k] for k in ['id','size','color','colors','price','enabled','available','image'] if k in v} for v in m['variants']]
   p['merch']['shippingProfiles']=[{**r,'variantIds':[str(v) for v in r['variantIds']]} for r in m.get('shippingProfiles',[])]
 return result

def register_catalog_sourcing(app,require_admin,path):
 store=CatalogSourcing(path)
 @app.get('/admin/catalog-sourcing')
 def read(request:Request):require_admin(request);return store.read()
 @app.post('/admin/catalog-sourcing')
 def save(request:Request,body:dict):require_admin(request);return {'references':store.save(body.get('products'))}
 @app.post('/admin/catalog-images')
 def image(request:Request,body:dict):
  require_admin(request);url=body.get('url','')
  if not isinstance(url,str) or len(url)>2000:raise HTTPException(400,'Choose a valid product image.')
  try:parsed=urlsplit(url);port=parsed.port
  except ValueError:raise HTTPException(400,'Choose a valid product image.') from None
  if parsed.scheme!='https' or parsed.hostname!='images-api.printify.com' or parsed.username or port not in {None,443}:raise HTTPException(400,'Unsupported product image host.')
  try:
   with httpx.stream('GET',url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://printify.com/'},follow_redirects=False,timeout=30) as response:
    response.raise_for_status();data=bytearray()
    for chunk in response.iter_bytes():
     data.extend(chunk)
     if len(data)>10*1024*1024:raise HTTPException(413,'Product image is too large.')
  except httpx.HTTPError:raise HTTPException(503,'Could not copy the product image. Upload it in the image editor instead.') from None
  mime='image/jpeg' if data[:3]==b'\xff\xd8\xff' else 'image/png' if data[:8]==b'\x89PNG\r\n\x1a\n' else None
  if not mime:raise HTTPException(400,'Use a JPEG or PNG product image.')
  return {'image':'data:'+mime+';base64,'+base64.b64encode(data).decode()}
 return store
