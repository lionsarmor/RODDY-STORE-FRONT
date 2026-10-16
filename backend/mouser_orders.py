"""Mouser direct shipping: exact cart previews and explicit paid-order submission.

Official schema: https://api.mouser.com/api/docs/V1
No POST is retried here. Supplier responses/URLs never enter public errors.
"""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
import re
from uuid import UUID
import httpx
from fastapi import HTTPException

class MouserUnavailable(Exception):pass
class MouserCostChanged(MouserUnavailable):pass

def money(value):
    try:
        n=Decimal(str(value).replace('$','').replace(',',''))
        if not n.is_finite() or not 0<=n<=999999:raise ValueError()
        return int((n*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    except (InvalidOperation,ValueError):raise MouserUnavailable('Mouser did not return a usable USD total.') from None

def shipping_address(address):
    fields={'CountryCode':('country',2),'FirstName':('first_name',22),'LastName':('last_name',23),
            'AddressOne':('address1',60),'AddressTwo':('address2',35),'City':('city',30),
            'StateOrProvince':('region',50),'PostalCode':('zip',10),'PhoneNumber':('phone',15)}
    result={}
    for dest,(source,limit) in fields.items():
        value=address.get(source,'')
        if source=='phone':value=re.sub(r'[^\d+]','',value)
        if len(value)>limit or (not value and source!='address2'):
            raise MouserUnavailable('The delivery address exceeds supplier field limits. Check the name, address and phone fields.')
        result[dest]=value
    result['AddressLocationTypeID']='Residential'
    return result

def matches_address(expected,actual):
    normalize=lambda v:re.sub(r'\s+','',str(v or '')).casefold()
    return isinstance(actual,dict) and all(normalize(expected.get(k))==normalize(actual.get(k)) for k in
        ['CountryCode','AddressOne','AddressTwo','City','StateOrProvince','PostalCode'])

def expected_lines(items):
    lines=Counter()
    for i in items:lines[i['supplier']['supplierSku']]+=i['qty']
    return lines

class MouserOrders:
    def __init__(self,config,reserve):
        self.config,self.reserve=config,reserve
        self.key=config.get('orderKey')
        if not self.key:raise MouserUnavailable('Mouser Order API is not connected.')
        self.fingerprint=hashlib.sha256(self.key.encode()).hexdigest()

    def call(self,path,payload=None,params=None):
        self.reserve('mouser')
        try:
            response=httpx.request('POST' if payload is not None else 'GET','https://api.mouser.com/api/v1/'+path,
                params={'apiKey':self.key,**(params or {})},json=payload,timeout=25)
            if not response.is_success:raise MouserUnavailable('Mouser request failed. Check the supplier connection; any submission must be reconciled before retrying.')
            data=response.json()
            if not isinstance(data,dict) or data.get('Errors'):raise MouserUnavailable('Mouser rejected this request. Check the account and item availability.')
            return data
        except (httpx.HTTPError,ValueError):raise MouserUnavailable('Mouser response unavailable. Any submission must be reconciled before retrying.') from None

    def enabled(self):
        if not self.config.get('automaticOrdering'):raise MouserUnavailable('Automatic Mouser fulfillment is disabled in supplier settings.')

    def options(self,address,cart=None):
        body={'CurrencyCode':'USD','ShippingAddress':shipping_address(address)}
        if cart:body['CartKey']=cart
        result=self.call('order/options/query',{'OrderInitialize':body}).get('OrderInitialize')
        if not isinstance(result,dict) or result.get('Errors') or result.get('CurrencyCode')!='USD':
            raise MouserUnavailable('Mouser account options are unavailable for this destination.')
        return result

    @staticmethod
    def card(options):
        cards=[];now=datetime.now(timezone.utc)
        for c in (options.get('Payment') or {}).get('PaymentTypes') or []:
            exp=re.search(r'\bExp\s+(0?[1-9]|1[0-2])/(\d{4}|\d{2})\b',str(c.get('Name','')),re.I)
            if not exp or not re.fullmatch(r'\d{4}',str(c.get('CreditCardLastFourDigits',''))):continue
            month,year=map(int,exp.groups());year=year+2000 if year<100 else year
            if (year,month)>=(now.year,now.month) and type(c.get('Method')) is int:cards.append(c)
        if len(cards)!=1:raise MouserUnavailable('Mouser needs exactly one identifiable unexpired saved card for automatic purchasing. Review saved cards in My Mouser.')
        return {k:cards[0][k] for k in ['Method','CreditCardLastFourDigits']}

    def quote(self,items,address):
        self.enabled()
        dest=shipping_address(address)
        lines=expected_lines(items)
        cart=self.call('cart/items/insert',{'CartItems':[{'MouserPartNumber':sku,'Quantity':qty,'PackagingChoice':'None'} for sku,qty in sorted(lines.items())],
                    'MouserPaysCustomsAndDuties':True}, {'countryCode':address['country'],'currencyCode':'USD'})
        key=cart.get('CartKey','')
        try:UUID(key)
        except (ValueError,TypeError,AttributeError):raise MouserUnavailable('Mouser did not return a new cart reference.') from None
        options=self.options(address,key);payment=self.card(options)
        methods=[]
        for method in (options.get('Shipping') or {}).get('Methods') or []:
            name=str(method.get('Method',''))
            if not re.search(r'UPS|FedEx|DHL|US Postal',name,re.I) or re.search(r'recipient|collect|freight|COD',name,re.I) or method.get('Rate') is None:continue
            if type(method.get('Code')) is int:methods.append((money(method['Rate']),method['Code'],name))
        if not methods:raise MouserUnavailable('No prepaid shipping quote is available for this destination.')
        rate,code,name=min(methods)
        request={'CurrencyCode':'USD','CartKey':key,'ShippingAddress':dest,'OrderType':'Complete',
                 'PrimaryShipping':{'Code':code},'Payment':{**payment,'TaxStatus':'Taxable'},'LanguageCode':'en-US'}
        snapshot={'automatic':True,'account':self.fingerprint,'request':request,'service':name,'currency':'USD'}
        preview=self.preview(snapshot,items,address)
        retail=sum(i['qty']*i['cents'] for i in items)
        # Shipping is passed through; supplier tax/fees are absorbed by retail markup.
        if preview['totalCents']>retail+preview['shippingCents']-round((retail+preview['shippingCents'])*.04)-30:
            raise MouserCostChanged('Mouser landed cost exceeds the retail allowance after a 4% + $0.30 payment-fee reserve. Review pricing.')
        return {**snapshot,**preview}

    def preview(self,snapshot,items,address,po=None):
        self.enabled()
        if snapshot.get('account')!=self.fingerprint:raise MouserUnavailable('Mouser account credentials changed. Review this order before purchasing.')
        body={**snapshot['request'],'SubmitOrder':False}
        if not matches_address(shipping_address(address),body.get('ShippingAddress')):raise MouserUnavailable('Mouser delivery snapshot does not match the customer address.')
        if po:body['Payment']={**body['Payment'],'PoNumber':po}
        result=self.call('order',{'Order':body}).get('Order')
        self.validate_order(result,items,address)
        if result.get('SubmitOrder') is True or result.get('OrderID') not in {None,'',0,'0'}:raise MouserUnavailable('Mouser returned an unexpected submitted order during preview. Review the supplier account.')
        shipping=result.get('ShippingMethod') or {}
        if shipping.get('PrimaryCode')!=body['PrimaryShipping']['Code']:raise MouserUnavailable('Mouser shipping service changed. Review this quote.')
        # Live API uses -1 for an unused secondary service (SecondaryCode=0).
        # Never treat a negative rate on a selected service as free shipping.
        secondary=money(shipping.get('SecondaryShippingRate')) if shipping.get('SecondaryCode') else 0
        return {'totalCents':money(result.get('OrderTotal')),'shippingCents':money(shipping.get('PrimaryShippingRate'))+secondary,
                'merchandiseCents':money(result.get('MerchandiseTotal')),'taxCents':money(result.get('TaxAmount'))}

    def validate_order(self,result,items,address):
        if not isinstance(result,dict) or result.get('Errors') or result.get('CurrencyCode')!='USD':raise MouserUnavailable('Mouser order summary is incomplete or rejected.')
        if any((result.get(k) or {}).get('Error') for k in ['BillingAddress','ShippingAddress','ShippingMethod','PaymentMethod']):raise MouserUnavailable('Mouser billing, shipping or payment needs attention.')
        if not matches_address(shipping_address(address),result.get('ShippingAddress')):raise MouserUnavailable('Mouser returned a different shipping address. Purchasing stopped.')
        lines=result.get('OrderLines')
        if not isinstance(lines,list):raise MouserUnavailable('Mouser order lines are missing.')
        actual=Counter()
        retail=Counter()
        for item in items:retail[item['supplier']['supplierSku']]+=item['qty']*item['cents']
        for line in lines:
            if line.get('Errors') or type(line.get('Quantity')) is not int or type(line.get('MouserATS')) is not int or line['MouserATS']<line['Quantity']:
                raise MouserUnavailable('Mouser cannot supply the complete quantity now.')
            actual[line.get('MouserPartNumber')]+=line['Quantity']
            if money(line.get('ExtendedPrice'))>=retail[line.get('MouserPartNumber')]:
                raise MouserCostChanged('Mouser item cost meets or exceeds its retail price. Review product pricing.')
        if actual!=expected_lines(items):raise MouserUnavailable('Mouser returned different parts or quantities. Purchasing stopped.')
        money(result.get('OrderTotal'))

    def submit(self,snapshot,po):
        self.enabled()
        body={**snapshot['request'],'Payment':{**snapshot['request']['Payment'],'PoNumber':po},'SubmitOrder':True}
        result=self.call('order',{'Order':body}).get('Order')
        if not isinstance(result,dict) or result.get('Errors') or not str(result.get('OrderID','')).isdigit() or int(result['OrderID'])<=0:
            raise MouserUnavailable('Mouser submission outcome is unknown. Reconcile by the store purchase reference before any retry.')
        return result

    def find(self,po):
        data=self.call('orderhistory/ByDateFilter',params={'dateFilter':'All'})
        entries=data.get('OrderHistoryItems')
        if not isinstance(entries,list):raise MouserUnavailable('Mouser order history is unavailable for reconciliation.')
        matches=[x for x in entries if x.get('PoNumber')==po]
        if len(matches)>1:raise MouserUnavailable('Multiple Mouser orders match this purchase reference. Review the supplier account.')
        if not matches:return None
        ident=str(matches[0].get('WebOrderNumber',''))
        if not ident.isdigit():raise MouserUnavailable('Mouser history did not return a web order reference.')
        return ident

    def order(self,ident,po,items,address):
        if not str(ident).isdigit():raise MouserUnavailable('Invalid Mouser order reference.')
        d=self.call('orderhistory/webOrderNumber',params={'webOrderNumber':ident})
        actual=Counter()
        for line in d.get('OrderLines') or []:actual[(line.get('ProductInfo') or {}).get('MouserPartNumber')]+=line.get('Quantity',0)
        if (str(d.get('WebOrderId'))!=str(ident) or d.get('CurrencyCode')!='USD'
                or (d.get('PaymentDetail') or {}).get('PoNumber')!=po or actual!=expected_lines(items)
                or not matches_address(shipping_address(address),d.get('ShippingAddress'))):
            raise MouserUnavailable('Mouser order identity, items or address did not match. Manual review required.')
        delivery=d.get('DeliveryDetail') or {};shipments=[]
        for s in delivery.get('TrackingDetails') or []:
            if s.get('Number'):shipments.append({'carrier':str(delivery.get('ShippingMethodName',''))[:100],
                'number':str(s['Number'])[:150],'url':s.get('Link','') if str(s.get('Link','')).startswith('https://') else ''})
        status=str(d.get('OrderStatusName','')).strip().lower()
        state='shipped' if status=='shipped' else 'canceled' if status in {'cancelled','canceled'} else 'submitted'
        return {'state':state,'shipments':shipments,'status':str(d.get('OrderStatusName',''))[:100],
                'totalCents':money((d.get('SummaryDetail') or {}).get('OrderTotal'))}
