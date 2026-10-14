"""Private order history, verified payment records and bookkeeping exports."""
import base64
import csv
import hashlib
import io
import json
import re
import time
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException


def iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat() if isinstance(value, (int, float)) and value else ''


def csv_value(value):
    value = '' if value is None else str(value)
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value


def dollars(value):
    return '' if value is None else f'{value/100:.2f}'


class OrderRecords:
    def __init__(self, connect):
        self.connect = connect
        with connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS order_finance (
              session TEXT PRIMARY KEY REFERENCES orders(session), status TEXT NOT NULL,
              captured INTEGER NOT NULL DEFAULT 0, refunded INTEGER NOT NULL DEFAULT 0,
              fees INTEGER, tax INTEGER, paid_at TEXT, verified INTEGER NOT NULL, details TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS payment_history (
              id INTEGER PRIMARY KEY AUTOINCREMENT, session TEXT NOT NULL REFERENCES orders(session),
              observed INTEGER NOT NULL, digest TEXT NOT NULL, details TEXT NOT NULL,
              UNIQUE(session,digest)
            );
            CREATE TABLE IF NOT EXISTS supplier_expenses (
              id TEXT PRIMARY KEY, session TEXT REFERENCES orders(session), created INTEGER NOT NULL,
              incurred TEXT NOT NULL, supplier TEXT NOT NULL, reference TEXT NOT NULL,
              amount INTEGER NOT NULL, currency TEXT NOT NULL, note TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS order_created ON orders(created DESC,request_id DESC);
            CREATE TABLE IF NOT EXISTS order_messages (
              id TEXT PRIMARY KEY, session TEXT NOT NULL REFERENCES orders(session),
              created INTEGER NOT NULL, recipient TEXT NOT NULL, subject TEXT NOT NULL,
              body TEXT NOT NULL, context TEXT NOT NULL, digest TEXT NOT NULL,
              UNIQUE(session,digest)
            );
            ''')

    def record(self, order, report):
        safe = {k: report.get(k) for k in ['status','captured','refunded','fees','tax','paidAt','payments']}
        safe['status'] = safe['status'] or 'unconfirmed'
        safe['captured'], safe['refunded'] = safe['captured'] or 0, safe['refunded'] or 0
        encoded = json.dumps(safe, sort_keys=True, separators=(',', ':'))
        now = int(time.time())
        with self.connect() as db:
            previous = db.execute('SELECT captured,paid_at FROM order_finance WHERE session=?',(order['session'],)).fetchone()
            # A later failed/canceled eligibility check cannot erase captured revenue.
            captured = max(safe['captured'],previous['captured'] if previous else 0)
            paid_at = previous['paid_at'] if previous and previous['paid_at'] else safe['paidAt']
            db.execute('''INSERT INTO order_finance VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(session) DO UPDATE SET
                status=excluded.status,captured=excluded.captured,refunded=excluded.refunded,
                fees=excluded.fees,tax=excluded.tax,paid_at=excluded.paid_at,verified=excluded.verified,details=excluded.details''',
                (order['session'],safe['status'],captured,safe['refunded'],safe['fees'],safe['tax'],paid_at,now,encoded))
            db.execute('INSERT OR IGNORE INTO payment_history(session,observed,digest,details) VALUES(?,?,?,?)',
                (order['session'],now,hashlib.sha256(encoded.encode()).hexdigest(),encoded))

    def summary(self, order):
        with self.connect() as db:
            row = db.execute('SELECT * FROM order_finance WHERE session=?',(order['session'],)).fetchone()
        if row:
            row = dict(row)
            return {**{k:row[k] for k in ['status','captured','refunded','fees','tax','verified']},'paidAt':row['paid_at'],
                    'netAfterFees':row['captured']-row['refunded']-row['fees'] if row['fees'] is not None else None}
        return {'status':'paid' if order['paid'] else 'canceled' if order.get('cancelled') else 'unconfirmed',
                'captured':order['amount'] if order['paid'] else 0,'refunded':0,'fees':None,'tax':None,
                'verified':None,'paidAt':None,'netAfterFees':None}

    def criteria(self, *, view='all', status='all', start=0, end=0, search=''):
        if not isinstance(view,str) or not isinstance(status,str) or view not in {'all','keycaps','office','attention','inbox','progress','shipped'} or status not in {'all','paid','refunded','partially-refunded','unconfirmed','canceled','processing','failed','payment-review'}:
            raise HTTPException(400,'Choose valid order filters.')
        if type(start) is not int or type(end) is not int or start<0 or end<0 or (end and end<=start) or not isinstance(search,str) or len(search)>100:
            raise HTTPException(400,'Check order dates and search.')
        where, args = ['1=1'], []
        if view=='inbox':where.append("o.paid=1 AND EXISTS(SELECT 1 FROM fulfillments q WHERE q.session=o.session AND q.state IN ('ready-to-order','awaiting-submission','ready-to-ship'))")
        if view=='progress':where.append("o.paid=1 AND EXISTS(SELECT 1 FROM fulfillments q WHERE q.session=o.session AND q.state NOT IN ('ready-to-order','awaiting-submission','ready-to-ship','shipped','delivered','canceled'))")
        if view=='shipped':where.append("o.paid=1 AND EXISTS(SELECT 1 FROM fulfillments q WHERE q.session=o.session) AND NOT EXISTS(SELECT 1 FROM fulfillments q WHERE q.session=o.session AND q.state NOT IN ('shipped','delivered','canceled'))")
        if view=='keycaps':where.append("o.paid=1 AND EXISTS(SELECT 1 FROM fulfillments q WHERE q.session=o.session AND q.kind='keycaps' AND q.state='awaiting-submission')")
        if view=='office':where.append("o.paid=1 AND EXISTS(SELECT 1 FROM fulfillments q WHERE q.session=o.session AND q.kind='office' AND q.state='ready-to-ship')")
        if view=='attention':where.append("EXISTS(SELECT 1 FROM fulfillments q WHERE q.session=o.session AND (q.error<>'' OR q.state='review'))")
        if status!='all':
            where.append("COALESCE(f.status,CASE WHEN o.paid=1 THEN 'paid' WHEN o.cancelled=1 THEN 'canceled' ELSE 'unconfirmed' END)=?");args.append(status)
        if start:where.append('o.created>=?');args.append(start)
        if end:where.append('o.created<?');args.append(end)
        if search:
            term='%'+search.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
            where.append("(o.request_id LIKE ? ESCAPE '\\' OR o.provider_id LIKE ? ESCAPE '\\' OR o.address LIKE ? ESCAPE '\\')");args.extend([term]*3)
        return ' AND '.join(where),args

    def page(self, *, cursor='', limit=50, **filters):
        if type(limit) is not int or not 1<=limit<=100:raise HTTPException(400,'Page size must be 1–100.')
        where,args=self.criteria(**filters)
        with self.connect() as db:
            count=db.execute('SELECT COUNT(*) FROM orders o LEFT JOIN order_finance f ON f.session=o.session WHERE '+where,args).fetchone()[0]
            if cursor:
                try:
                    if len(cursor)>180:raise ValueError()
                    created,reference=json.loads(base64.urlsafe_b64decode(cursor+'='*(-len(cursor)%4)))
                    if type(created) is not int or created<0 or not re.fullmatch(r'[a-zA-Z0-9-]{1,100}',reference):raise ValueError()
                except Exception:raise HTTPException(400,'Invalid order cursor.') from None
                where+=' AND (o.created<? OR (o.created=? AND o.request_id<?))';args.extend([created,created,reference])
            rows=db.execute('SELECT o.* FROM orders o LEFT JOIN order_finance f ON f.session=o.session WHERE '+where+' ORDER BY o.created DESC,o.request_id DESC LIMIT ?',args+[limit+1]).fetchall()
        more=len(rows)>limit;rows=[dict(r) for r in rows[:limit]]
        next_cursor=base64.urlsafe_b64encode(json.dumps([rows[-1]['created'],rows[-1]['request_id']]).encode()).decode().rstrip('=') if more else ''
        return rows,{'has_more':more,'next_cursor':next_cursor,'total':count}

    def dashboard(self, start=0, end=0, search=''):
        totals={}
        with self.connect() as db:
            for view in ['inbox','progress','shipped','attention','all']:
                where,args=self.criteria(view=view,start=start,end=end,search=search)
                totals[view]=db.execute('SELECT COUNT(*) FROM orders o LEFT JOIN order_finance f ON f.session=o.session WHERE '+where,args).fetchone()[0]
            where,args=self.criteria(start=start,end=end,search=search)
            row=db.execute('SELECT COALESCE(SUM(COALESCE(f.captured,CASE WHEN o.paid=1 THEN o.amount ELSE 0 END)),0),COALESCE(SUM(f.refunded),0) FROM orders o LEFT JOIN order_finance f ON f.session=o.session WHERE '+where,args).fetchone()
            totals.update(capturedCents=row[0],refundedCents=row[1])
        return totals

    def expense(self, reference, body):
        amount=body.get('amountCents');currency=body.get('currency','USD');incurred=body.get('date','')
        if type(amount) is not int or not 0<amount<=100000000 or currency not in {'USD','CAD','EUR','GBP','PHP'}:
            raise HTTPException(400,'Enter a positive supplier expense and its invoice currency.')
        try:datetime.strptime(incurred,'%Y-%m-%d')
        except (ValueError,TypeError):raise HTTPException(400,'Enter the invoice date.') from None
        values={}
        for field,maximum in [('supplier',80),('reference',150),('note',500)]:
            value=body.get(field,'')
            if not isinstance(value,str) or len(value)>maximum or any(ord(c)<32 for c in value):raise HTTPException(400,'Check the supplier expense fields.')
            values[field]=value.strip()
        if not values['supplier'] or not values['reference']:raise HTTPException(400,'Enter supplier and invoice/order reference.')
        with self.connect() as db:
            order=db.execute('SELECT session FROM orders WHERE request_id=?',(reference,)).fetchone()
            if not order:raise HTTPException(404,'Order not found.')
            existing=db.execute('SELECT id FROM supplier_expenses WHERE session=? AND supplier=? AND reference=?',(order['session'],values['supplier'],values['reference'])).fetchone()
            if existing:raise HTTPException(409,'That supplier invoice is already recorded for this order.')
            ident=str(uuid4());db.execute('INSERT INTO supplier_expenses VALUES(?,?,?,?,?,?,?,?,?)',
                (ident,order['session'],int(time.time()),incurred,values['supplier'],values['reference'],amount,currency,values['note']))
        return {'saved':True,'id':ident}

    def expenses(self, session):
        with self.connect() as db:return [dict(r) for r in db.execute('SELECT id,incurred,supplier,reference,amount,currency,note FROM supplier_expenses WHERE session=? ORDER BY created',(session,))]

    def message_context(self, order):
        # Bind an owner's sent confirmation to the customer-facing shipment data.
        # Supplier references, costs and manufacturing files never enter emails.
        with self.connect() as db:
            rows=db.execute('SELECT kind,state,shipments FROM fulfillments WHERE session=? ORDER BY kind',(order['session'],)).fetchall()
        items=json.loads(order['items'])
        value={'address':json.loads(order['address']) if order['address'] else None,
               'items':[{k:i.get(k) for k in ['name','qty','kind']} for i in items],
               'fulfillments':[{'kind':row['kind'],'dispatched':row['state'] in ['shipped','delivered','canceled'],
                                'shipments':[{k:s.get(k,'') for k in ['carrier','number','url']} for s in json.loads(row['shipments'])]} for row in rows]}
        return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def messages(self, session):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT id,created,recipient,subject,body,context FROM order_messages WHERE session=? ORDER BY created DESC,id DESC',(session,))]

    def record_message(self, reference, body):
        if body.get('confirmedSent') is not True:
            raise HTTPException(400,'Mark this only after you have sent the message from your email account.')
        subject,content=body.get('subject'),body.get('body')
        if (not isinstance(subject,str) or not subject.strip() or len(subject)>200 or any(ord(c)<32 for c in subject)
                or not isinstance(content,str) or not content.strip() or len(content)>20000
                or any(ord(c)<32 and c not in '\n\r\t' for c in content)):
            raise HTTPException(400,'Enter a subject and message within the displayed limits.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM orders WHERE request_id=?',(reference,)).fetchone()
            if not row:raise HTTPException(404,'Order not found.')
            order=dict(row)
            if not order['paid'] or self.summary(order)['status']!='paid':raise HTTPException(409,'Only confirmed paid orders can be marked contacted here.')
            address=json.loads(order['address']) if order['address'] else {}
            recipient=address.get('email','')
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',recipient):raise HTTPException(409,'This order has no valid customer email address.')
            context=self.message_context(order)
            if body.get('context')!=context:raise HTTPException(409,'The delivery details changed. Reopen the thank-you draft and check the latest tracking before recording it.')
            digest=hashlib.sha256(json.dumps([recipient,subject.strip(),content.strip(),context],ensure_ascii=False).encode()).hexdigest()
            ident=str(uuid4())
            db.execute('INSERT OR IGNORE INTO order_messages VALUES(?,?,?,?,?,?,?,?)',
                (ident,order['session'],int(time.time()),recipient,subject.strip(),content.strip(),context,digest))
            ident=db.execute('SELECT id FROM order_messages WHERE session=? AND digest=?',(order['session'],digest)).fetchone()[0]
        return {'saved':True,'id':ident}

    def export(self, kind='orders', **filters):
        if kind not in {'orders','items','expenses','payments'}:raise HTTPException(400,'Choose an export type.')
        where,args=self.criteria(**filters);out=io.StringIO(newline='');writer=csv.writer(out)
        columns={'orders':['order_reference','square_order_id','created_utc','paid_at_utc','payment_status','currency','subtotal','shipping','tax','order_total','captured','refunded','processing_fees','net_after_fees','verified_utc','customer_email','fulfillment'],
                 'items':['order_reference','created_utc','payment_status','product_id','product_name','kind','variant','quantity','currency','unit_price','line_total','design_revision'],
                 'expenses':['order_reference','invoice_date','supplier','invoice_reference','amount','currency','note'],
                 'payments':['order_reference','observed_utc','payment_record']}
        writer.writerow(columns[kind])
        with self.connect() as db:
            for row in db.execute('SELECT o.* FROM orders o LEFT JOIN order_finance f ON f.session=o.session WHERE '+where+' ORDER BY o.created,o.request_id',args):
                order=dict(row);finance=self.summary(order);items=json.loads(order['items']);ref='RODDY-'+order['request_id']
                if kind=='orders':
                    address=json.loads(order['address']) if order['address'] else {}
                    fulfillment='; '.join(r['kind']+':'+r['state'] for r in db.execute('SELECT kind,state FROM fulfillments WHERE session=?',(order['session'],)))
                    writer.writerow([csv_value(v) for v in [ref,order['provider_id'],iso(order['created']),finance['paidAt'],finance['status'],'USD',dollars(order['amount']-order['shipping']-(finance['tax'] or 0)),dollars(order['shipping']),dollars(finance['tax']),dollars(order['amount']),dollars(finance['captured']),dollars(finance['refunded']),dollars(finance['fees']),dollars(finance['netAfterFees']),iso(finance['verified']),address.get('email',''),fulfillment]])
                elif kind=='items':
                    for item in items:writer.writerow([csv_value(v) for v in [ref,iso(order['created']),finance['status'],item['id'],item['name'],item.get('kind','digital'),item.get('label',''),item.get('qty',1),'USD',dollars(item['cents']),dollars(item['cents']*item.get('qty',1)),item.get('designSnapshot',{}).get('templateRevision','')]])
                elif kind=='expenses':
                    for expense in self.expenses(order['session']):writer.writerow([csv_value(v) for v in [ref,expense['incurred'],expense['supplier'],expense['reference'],dollars(expense['amount']),expense['currency'],expense['note']]])
                else:
                    for event in db.execute('SELECT observed,details FROM payment_history WHERE session=? ORDER BY id',(order['session'],)):writer.writerow([csv_value(ref),iso(event['observed']),event['details']])
        return ('\ufeff'+out.getvalue()).encode('utf-8')
