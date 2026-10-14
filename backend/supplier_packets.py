"""Owner-only manual procurement packets from the paid checkout snapshot."""
import io,json,zipfile

def supplier_packet_zip(order,kind):
    items=json.loads(order['items']) if isinstance(order['items'],str) else order['items']
    address=json.loads(order['address']) if isinstance(order['address'],str) else order['address']
    details={'orderReference':'RODDY-'+order['request_id'],'supplier':kind,'currency':'USD','customerPaidCents':order['amount'],
             'delivery':address,'items':[{'product':i['name'],'quantity':i['qty'],'supplier':i['supplier'],'quotedProcurement':i['procurement']} for i in items if i.get('kind')==kind],
             'instructions':'Place the supplier order manually with this exact variant, quantity and delivery address. Verify the current supplier total. Record its order reference and actual invoice cost in RODDY Orders, then add tracking. Downloading this file does not place an order.'}
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w',compression=zipfile.ZIP_DEFLATED) as archive:archive.writestr('ORDER_DETAILS.json',json.dumps(details,indent=2)+'\n')
    return data.getvalue()
