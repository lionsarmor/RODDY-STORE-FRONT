"""One owner-controlled landed-cost markup policy for automatic suppliers."""
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
import time
from fastapi import HTTPException

DEFAULTS={'enabled':False,'markupPercent':30,'feePercent':4,'feeFixed':.30,'unknownTaxPercent':10,'round99':True}

class Pricing:
    def __init__(self,connect):
        self.connect=connect
        with connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS automatic_pricing(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL,data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS live_prices(product TEXT NOT NULL,variant TEXT NOT NULL,data TEXT NOT NULL,checked INTEGER NOT NULL,PRIMARY KEY(product,variant));''')
            db.execute('INSERT OR IGNORE INTO automatic_pricing VALUES(1,1,?)',(json.dumps(DEFAULTS),))
    def settings(self):
        with self.connect() as db:r=db.execute('SELECT * FROM automatic_pricing WHERE id=1').fetchone()
        return {**DEFAULTS,**json.loads(r['data']),'revision':r['revision']}
    def save(self,body):
        if type(body.get('enabled')) is not bool or type(body.get('round99')) is not bool:raise HTTPException(400,'Check the pricing options.')
        clean={k:body[k] for k in ['enabled','round99']}
        for k,maximum in [('markupPercent',500),('feePercent',25),('feeFixed',100),('unknownTaxPercent',50)]:
            v=body.get(k)
            if type(v) not in (int,float) or not 0<=v<=maximum or abs(v*100-round(v*100))>.000001:raise HTTPException(400,'Use valid pricing amounts with up to two decimals.')
            clean[k]=v
        with self.connect() as db:
            r=db.execute('UPDATE automatic_pricing SET data=?,revision=revision+1 WHERE id=1 AND revision=?',(json.dumps(clean),body.get('revision')))
            if not r.rowcount:raise HTTPException(409,'Pricing settings changed. Reload before saving.')
            db.execute('DELETE FROM live_prices')
        return self.settings()
    @staticmethod
    def automatic(product):
        return bool(product.get('merch') or (product.get('supplier') or {}).get('fulfillment')=='automatic')
    def applies(self,product):
        return self.settings()['enabled'] and self.automatic(product) and product.get('pricingMode','automatic')!='fixed'
    def retail(self,landed,shipping=0,floor=0,rules=None):
        r=rules or self.settings();d=lambda n:Decimal(str(n))
        # Mark up the complete landed cost, cover estimated payment fees, then
        # remove the pass-through shipping shown separately to the customer.
        total=(d(landed)*(1+d(r['markupPercent'])/100)+d(r['feeFixed'])*100)/(1-d(r['feePercent'])/100)
        price=max(int((total-d(shipping)).quantize(Decimal('1'),rounding=ROUND_CEILING)),floor)
        if r['round99']:price=((price+1+99)//100)*100-1
        if not 0<price<=99999999:raise HTTPException(409,'The calculated retail price needs review.')
        return price
    def reprice(self,items,total,shipping,goods,rules=None):
        r=rules or self.settings();weights=[Decimal(str(goods.get(i['supplier']['supplierSku'],0))) for i in items]
        denominator=sum(weights)
        if denominator<=0:raise HTTPException(409,'A current supplier cost is unavailable.')
        # Items with the same supplier SKU are not valid catalog duplicates.
        return [self.retail(Decimal(total)*w/denominator/i['qty'],Decimal(shipping)*w/denominator/i['qty'],i.get('pricingFloorCents',0),r) for i,w in zip(items,weights)]
    @staticmethod
    def signature(product):
        fields={k:product.get(k) for k in ['supplier','merch','fulfillmentRef','pricingFloor','pricingMode','shippingCountries']}
        return hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    @staticmethod
    def variants(product):
        return {v['id'] for v in product['merch']['variants'] if v.get('enabled')} if product.get('merch') else {''}
    def record(self,product,variant,price,available,revision,error='',landed=None,shipping=None,signature=None):
        data={'priceCents':price,'available':available,'revision':revision,'error':error,'landedCents':landed,'shippingCents':shipping,'signature':signature}
        with self.connect() as db:db.execute('INSERT INTO live_prices VALUES(?,?,?,?) ON CONFLICT(product,variant) DO UPDATE SET data=excluded.data,checked=excluded.checked',(product,variant,json.dumps(data),int(time.time())))
    def rows(self):
        with self.connect() as db:return [{**json.loads(r['data']),'id':r['product'],'variantId':r['variant'],'checkedAt':r['checked']} for r in db.execute('SELECT * FROM live_prices')]
    def public(self,catalog):
        policy=self.settings();rows=self.rows();result=[];pending=[]
        for p in catalog['products']:
            if not p.get('active') or p.get('status')!='available' or not policy['enabled'] or not self.automatic(p) or p.get('pricingMode','automatic')=='fixed':continue
            valid=[r for r in rows if r['id']==p['id'] and r['revision']==policy['revision'] and r['checkedAt']>time.time()-3600 and r.get('signature')==self.signature(p) and r['variantId'] in self.variants(p)]
            if {r['variantId'] for r in valid}!=self.variants(p) or not valid or not any(r['available'] for r in valid):
                pending.append(p['id'])
                continue
            for r in valid:result.append({k:r[k] for k in ['id','variantId','priceCents','available','checkedAt']})
        return {'prices':result,'pricingPendingProducts':pending}
