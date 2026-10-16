"""Refresh public price estimates without publishing supplier costs or addresses."""
import math
import time
from .mouser_orders import shipping_address

class PricingRefresh:
    def __init__(self,commerce):
        self.commerce=commerce;self.address=None;self.address_checked=0
    def destination(self):
        if self.address is None or self.address_checked<time.time()-3600:
            client=self.commerce.mouser_factory()
            raw=client.call('order/options/query',{'OrderInitialize':{'CurrencyCode':'USD'}})['OrderInitialize']['ShippingAddress']
            mapping={'first_name':'FirstName','last_name':'LastName','country':'CountryCode','region':'StateOrProvince','address1':'AddressOne','address2':'AddressTwo','city':'City','zip':'PostalCode','phone':'PhoneNumber'}
            self.address={k:raw.get(v) or '' for k,v in mapping.items()};shipping_address(self.address)
            self.address_checked=time.time()
        return self.address
    def run(self):
        c=self.commerce;rules=c.pricing.settings()
        if not rules['enabled']:return
        rows=c.pricing.rows()
        for p in c.catalog()['products']:
            if not p.get('active') or p.get('status')!='available' or not c.pricing.automatic(p) or p.get('pricingMode','automatic')=='fixed':continue
            old=[r for r in rows if r['id']==p['id'] and r['revision']==rules['revision'] and r.get('signature')==c.pricing.signature(p) and r['variantId'] in c.pricing.variants(p)]
            if old and {r['variantId'] for r in old}==c.pricing.variants(p) and min(r['checkedAt'] for r in old)>time.time()-(300 if any(r['error'] for r in old) else 1800):continue
            floor=round(p.get('pricingFloor',0)*100)
            try:
                if p.get('merch'):
                    supplier=c.printify();product=supplier.product(p['merch']['productId'])
                    for variant in p['merch']['variants']:
                        if not variant.get('enabled'):continue
                        actual=next((v for v in product['variants'] if v['id']==variant['providerVariantId']),{})
                        rates=[r['firstItem'] for r in product.get('shippingProfiles',[]) if 'US' in r.get('countries',[]) and variant['providerVariantId'] in r.get('variantIds',[])]
                        cost=actual.get('costCents');available=actual.get('available') is True and actual.get('enabled') is True and type(cost) is int and bool(rates)
                        shipping=round(min(rates)*100) if rates else 0
                        price=c.pricing.retail((cost+shipping)*(1+rules['unknownTaxPercent']/100),shipping,floor,rules) if available else None
                        c.pricing.record(p['id'],variant['id'],price,available,rules['revision'],landed=round((cost+shipping)*(1+rules['unknownTaxPercent']/100)) if available else None,shipping=shipping,signature=c.pricing.signature(p))
                else:
                    s=p['supplier'];multiple=max(1,s.get('orderMultiple',1));quantity=math.ceil(max(1,s.get('minimumQuantity',1))/multiple)*multiple
                    item={'id':p['id'],'supplier':s,'qty':quantity,'cents':round(p['price']*100),'pricingFloorCents':floor}
                    quote=c.mouser_factory().quote([item],self.destination(),pricing=lambda items,total,shipping,goods:c.pricing.reprice(items,total,shipping,goods,rules))
                    c.pricing.record(p['id'],'',item['cents'],True,rules['revision'],landed=round(quote['totalCents']/quantity),shipping=round(quote['shippingCents']/quantity),signature=c.pricing.signature(p))
            except Exception:
                # A failed supplier read never becomes a zero price or assumed stock.
                for variant in ([v['id'] for v in p['merch']['variants'] if v.get('enabled')] if p.get('merch') else ['']):
                    c.pricing.record(p['id'],variant,None,False,rules['revision'],'Supplier price/availability could not be refreshed. Check its connection and product setup.',signature=c.pricing.signature(p))
            return # Spread upstream reads across worker ticks and respect shared quotas.
