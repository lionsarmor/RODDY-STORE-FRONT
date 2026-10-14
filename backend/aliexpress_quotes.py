"""Read-only AliExpress DS availability and delivery quotes.

Calls use the existing server-held buyer token. Supplier purchasing and payment are manual.
"""
import json
import re
from fastapi import HTTPException
from .supplier_clients import AliExpress,money,number,link

STATES=dict(part.split(':',1) for part in 'AL:Alabama|AK:Alaska|AZ:Arizona|AR:Arkansas|CA:California|CO:Colorado|CT:Connecticut|DE:Delaware|DC:District of Columbia|FL:Florida|GA:Georgia|HI:Hawaii|ID:Idaho|IL:Illinois|IN:Indiana|IA:Iowa|KS:Kansas|KY:Kentucky|LA:Louisiana|ME:Maine|MD:Maryland|MA:Massachusetts|MI:Michigan|MN:Minnesota|MS:Mississippi|MO:Missouri|MT:Montana|NE:Nebraska|NV:Nevada|NH:New Hampshire|NJ:New Jersey|NM:New Mexico|NY:New York|NC:North Carolina|ND:North Dakota|OH:Ohio|OK:Oklahoma|OR:Oregon|PA:Pennsylvania|RI:Rhode Island|SC:South Carolina|SD:South Dakota|TN:Tennessee|TX:Texas|UT:Utah|VT:Vermont|VA:Virginia|WA:Washington|WV:West Virginia|WI:Wisconsin|WY:Wyoming|AB:Alberta|BC:British Columbia|MB:Manitoba|NB:New Brunswick|NL:Newfoundland and Labrador|NS:Nova Scotia|NT:Northwest Territories|NU:Nunavut|ON:Ontario|PE:Prince Edward Island|QC:Quebec|SK:Saskatchewan|YT:Yukon'.split('|'))


def response(data, method):
    return data.get(method.replace('.','_')+'_response',data)


class AliExpressQuotes:
    def __init__(self,config,reserve=lambda *_:None):
        if not all(config.get(k) for k in ['appKey','appSecret','accessToken']):
            raise HTTPException(409,'This item is temporarily unavailable. Contact RODDY for availability.')
        self.client=AliExpress(config,reserve)

    def quote(self,item,address):
        mapping=item['supplier'];sku=mapping['supplierSku'];variant_id=mapping['variantId']
        raw=response(self.client.call('aliexpress.ds.product.get',{'ship_to_country':address['country'],'product_id':sku,'target_currency':'USD','target_language':'EN','remove_personal_benefit':'true'},True),'aliexpress.ds.product.get').get('result',{})
        store=raw.get('ae_store_info',{})
        if mapping.get('sellerId') and str(store.get('store_id'))!=mapping['sellerId']:
            raise HTTPException(409,'This product needs an availability update.')
        variants=raw.get('ae_item_sku_info_dtos',[])
        if isinstance(variants,dict):variants=variants.get('ae_item_sku_info_d_t_o',[])
        variant=next((v for v in variants if str(v.get('sku_id'))==variant_id),None)
        if not variant or variant.get('currency_code')!='USD':raise HTTPException(409,'This keyboard selection is unavailable.')
        stock=number(variant.get('sku_available_stock'));cost=money(variant.get('offer_sale_price') or variant.get('sku_price'))
        if stock is None or stock<item['qty'] or cost is None:raise HTTPException(409,'There is not enough stock for this selection.')
        attributes=variant.get('sku_attr')
        if not attributes:
            props=variant.get('ae_sku_property_dtos',[])
            if isinstance(props,dict):props=props.get('ae_sku_property_d_t_o',[])
            attributes=';'.join(str(p['sku_property_id'])+':'+str(p['property_value_id']) for p in props if p.get('sku_property_id') is not None and p.get('property_value_id') is not None)
        if not attributes:raise HTTPException(409,'This selection needs a supplier variant update.')
        req={'quantity':item['qty'],'shipToCountry':address['country'],'productId':sku,'selectedSkuId':variant_id,'province':STATES.get(address['region'],address['region']),'language':'en_US','locale':'en_US','currency':'USD'}
        freight=response(self.client.call('aliexpress.ds.freight.query',{'queryDeliveryReq':json.dumps(req,separators=(',',':'))},True),'aliexpress.ds.freight.query').get('result',{})
        if freight.get('success') is not True:raise HTTPException(409,'Shipping is unavailable to this address.')
        options=[]
        for option in freight.get('delivery_options',[]):
            # Despite its name, the official field is a decimal currency amount
            # (live response: shipping_fee_cent="1.99", shipping_fee_format="$1.99").
            shipping=0 if option.get('free_shipping') else money(option.get('shipping_fee_cent'))
            if option.get('shipping_fee_currency')=='USD' and shipping is not None and option.get('tracking') is True and option.get('code'):
                options.append((shipping,option))
        if not options:raise HTTPException(409,'Tracked shipping is unavailable to this address.')
        shipping,option=min(options,key=lambda x:x[0]);total=cost*item['qty']+shipping
        # Supplier cost cannot consume the customer payment or its processing allowance.
        if total>item['cents']*item['qty']+shipping-max(500,round((item['cents']*item['qty']+shipping)*.04)):
            raise HTTPException(409,'This product needs a price update. Please try again later.')
        return {'unitCostCents':cost,'shippingCents':shipping,'totalCents':total,'currency':'USD','skuAttr':attributes,
                'service':option['code'],'minimumDays':option.get('min_delivery_days'),'maximumDays':option.get('max_delivery_days')}
