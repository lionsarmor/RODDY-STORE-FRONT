"""Durable Mouser outbox; ambiguous submissions are only reconciled, never retried."""
from datetime import datetime, timezone
import json
import time
from fastapi import HTTPException
from .mouser_orders import MouserUnavailable, MouserCostChanged, money


def initialize(connect):
    with connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS mouser_purchases(
            session TEXT PRIMARY KEY,po TEXT NOT NULL UNIQUE,state TEXT NOT NULL,
            supplier_id TEXT,total INTEGER,created INTEGER NOT NULL)''')


def process(commerce,order):
    items=commerce.automatic_mouser(json.loads(order['items']))
    if not items:return
    session=order['session'];snapshot=items[0]['procurement'];address=json.loads(order['address'])
    f=next((f for f in commerce.fulfillments(session) if f['kind']=='mouser'),None)
    if not f or f['state'] in {'delivered','canceled'}:return
    po='RD'+order['request_id'].replace('-','')[:18]
    try:
        client=commerce.mouser_factory()
        with commerce.connect() as db:
            db.execute('INSERT OR IGNORE INTO mouser_purchases(session,po,state,created) VALUES(?,?,?,?)',(session,po,'prepared',int(time.time())))
            purchase=dict(db.execute('SELECT * FROM mouser_purchases WHERE session=?',(session,)).fetchone())
        ident=purchase['supplier_id']
        if not ident:
            if purchase['state']=='prepared':
                if f['state'] not in {'queued','review'}:return
                commerce.holds.check(items)
                preview=client.preview(snapshot,items,address,po)
                if preview['totalCents']>snapshot['totalCents']:
                    raise MouserCostChanged('Mouser cost increased above the accepted quote. Purchasing stopped; review this order and product pricing.')
                # Payment is checked immediately before the irreversible supplier call.
                paid=commerce.check_payment(order)
                if not paid:
                    commerce.mark_paid(order,False);return
                with commerce.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    changed=db.execute("UPDATE mouser_purchases SET state='submitting' WHERE session=? AND state='prepared'",(session,)).rowcount
                if not changed:return
                commerce.update(session,'mouser','submitting')
                try:
                    result=client.submit(snapshot,po)
                except HTTPException as exc:
                    # Local request budget rejects before network I/O. Only this
                    # known non-submission may return to prepared automatically.
                    if exc.status_code==429:
                        with commerce.connect() as db:db.execute("UPDATE mouser_purchases SET state='prepared' WHERE session=? AND state='submitting'",(session,))
                    raise
                ident=str(result['OrderID'])
                # Save the reference before parsing cost or making another request.
                with commerce.connect() as db:db.execute("UPDATE mouser_purchases SET state='submitted',supplier_id=? WHERE session=?",(ident,session))
                commerce.update(session,'mouser','submitted',ident)
                reported_cost=money(result.get('OrderTotal'))
                if reported_cost>snapshot['totalCents']:
                    commerce.holds.suspend(items,'Mouser accepted a total above the preview. Review this supplier order and product pricing.')
            else:
                ident=client.find(po)
                if not ident:raise MouserUnavailable('Submission outcome unknown. Check Mouser for purchase reference '+po+'. No repeat purchase will be attempted.')
                # Verify PO + items + destination before accepting a history match.
                client.order(ident,po,items,address)
                with commerce.connect() as db:db.execute("UPDATE mouser_purchases SET state='submitted',supplier_id=? WHERE session=?",(ident,session))
                commerce.update(session,'mouser','submitted',ident)
        current=client.order(ident,po,items,address)
        cost=current['totalCents']
        with commerce.connect() as db:db.execute('UPDATE mouser_purchases SET total=? WHERE session=?',(cost,session))
        issue=''
        if cost>snapshot['totalCents']:
            issue='Mouser reported a higher total after submission. Review the supplier order and pricing; new purchases of these items are suspended.'
            commerce.holds.suspend(items,issue)
        commerce.update(session,'mouser',current['state'],ident,issue,current['shipments'])
        # Order cost is an expense record, not a claim that card settlement cleared.
        if not any(e['supplier']=='Mouser' and e['reference']==ident for e in commerce.records.expenses(session)):
            commerce.records.expense(order['request_id'],{'supplier':'Mouser','reference':ident,'amountCents':cost,'currency':'USD',
                'date':datetime.now(timezone.utc).strftime('%Y-%m-%d'),'note':'Automatic supplier order total; verify the final invoice and card settlement in Mouser.'})
    except MouserCostChanged as exc:
        commerce.holds.suspend(items,str(exc));commerce.update(session,'mouser','review',error=str(exc))
    except (MouserUnavailable,HTTPException) as exc:
        message=exc.detail if isinstance(exc,HTTPException) else str(exc)
        commerce.update(session,'mouser','review',error=message+' Purchase reference: '+po+'.')
    except (KeyError,TypeError,ValueError,AttributeError):
        commerce.update(session,'mouser','review',error='Mouser returned incomplete order data. Review the supplier reference; no automatic repeat submission will be made.')
