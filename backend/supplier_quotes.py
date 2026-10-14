"""Read-only stock/pricing checks for manually placed supplier orders."""
from fastapi import HTTPException
from .aliexpress_quotes import AliExpressQuotes
from .supplier_clients import Mouser

class MouserQuotes:
    def __init__(self,config,reserve):
        if not config.get('searchKey'):raise HTTPException(409,'This item is temporarily unavailable.')
        self.client=Mouser(config,reserve)
    def quote(self,item,address):
        product=self.client.product(item['supplier']['supplierSku'],address['country'])
        quantity=item['qty'];minimum=product['minimumQuantity'];multiple=product['orderMultiple']
        if quantity<minimum or quantity%multiple or product['availableQuantity'] is None or quantity>product['availableQuantity']:
            raise HTTPException(409,'This quantity is unavailable. Check the item minimum and availability.')
        prices=[b for b in product['priceBreaks'] if b['currency']=='USD' and type(b['quantity']) is int and b['quantity']<=quantity and b['costCents'] is not None]
        if not prices:raise HTTPException(409,'A current price is unavailable for this item.')
        cost=max(prices,key=lambda b:b['quantity'])['costCents'];rate=item.get('officeShipping',{}).get(address['country'])
        if not isinstance(rate,dict):raise HTTPException(409,'Shipping is not configured for this product and country.')
        from .commerce import cents
        shipping=cents(rate['firstItem'])+cents(rate['additionalItem'])*(quantity-1)
        if cost*quantity>item['cents']*quantity-round((item['cents']*quantity+shipping)*.04):
            raise HTTPException(409,'This product needs a price update. Please try again later.')
        return {'unitCostCents':cost,'shippingCents':shipping,'totalCents':cost*quantity+shipping,'currency':'USD','service':'Owner-arranged shipping'}

def supplier_quote_client(kind,config,reserve):
    if kind=='aliexpress':return AliExpressQuotes(config,reserve)
    if kind=='mouser':return MouserQuotes(config,reserve)
    raise HTTPException(409,'This item is temporarily unavailable.')
