import csv,io,json,sqlite3,tempfile,unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException
from backend.order_records import OrderRecords
from backend.square import Square

class OrderRecordTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)/'orders.db'
        @contextmanager
        def connect():
            db=sqlite3.connect(self.path);db.row_factory=sqlite3.Row
            try:
                with db:yield db
            finally:db.close()
        self.connect=connect
        with connect() as db:
            db.executescript('CREATE TABLE orders(request_id TEXT PRIMARY KEY,session TEXT UNIQUE,provider_id TEXT,created INTEGER,paid INTEGER,cancelled INTEGER,amount INTEGER,shipping INTEGER,items TEXT,address TEXT);CREATE TABLE fulfillments(session TEXT,kind TEXT,state TEXT,error TEXT);')
        self.records=OrderRecords(connect)
    def order(self,created=100,paid=1):
        ident=str(uuid4());row={'request_id':ident,'session':ident,'provider_id':'square-'+ident,'created':created,'paid':paid,'cancelled':0,'amount':11500,'shipping':1500,'items':json.dumps([{'id':'keys','name':'=EVIL()','qty':2,'cents':5000,'kind':'keycaps','designSnapshot':{'templateRevision':'v6'}}]),'address':json.dumps({'email':'buyer@example.com'})}
        with self.connect() as db:db.execute('INSERT INTO orders VALUES(:request_id,:session,:provider_id,:created,:paid,:cancelled,:amount,:shipping,:items,:address)',row)
        return row
    def test_full_history_paginates_without_losing_equal_timestamp_orders(self):
        expected={self.order()['request_id'] for _ in range(125)};found=[];cursor=''
        while True:
            rows,page=self.records.page(cursor=cursor,limit=20);self.assertEqual(page['total'],125);found.extend(r['request_id'] for r in rows);cursor=page['next_cursor']
            if not cursor:break
        self.assertEqual(len(found),125);self.assertEqual(set(found),expected)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(self.records.export().decode('utf-8-sig'))))),125)
    def test_refund_keeps_captured_revenue_and_missing_fees_blank(self):
        o=self.order();report={'status':'paid','captured':11500,'refunded':0,'fees':None,'tax':0,'paidAt':'2026-10-14T12:00:00Z','payments':[]}
        self.records.record(o,report);self.records.record(o,report)
        self.records.record(o,{**report,'status':'partially-refunded','refunded':2500})
        with self.connect() as db:db.execute('UPDATE orders SET paid=0 WHERE session=?',(o['session'],));self.assertEqual(db.execute('SELECT COUNT(*) FROM payment_history').fetchone()[0],2)
        o['paid']=0;finance=self.records.summary(o);self.assertEqual(finance['captured'],11500);self.assertEqual(finance['refunded'],2500);self.assertIsNone(finance['netAfterFees'])
        rows,page=self.records.page(status='partially-refunded');self.assertEqual(len(rows),1)
        exported=next(csv.DictReader(io.StringIO(self.records.export().decode('utf-8-sig'))));self.assertEqual(exported['captured'],'115.00');self.assertEqual(exported['processing_fees'],'');self.assertEqual(exported['refunded'],'25.00')
        self.records.record(o,{**report,'status':'refunded','refunded':11500,'fees':360});self.assertEqual(self.records.summary(o)['netAfterFees'],-360)
    def test_line_export_uses_frozen_values_and_prevents_spreadsheet_formulas(self):
        self.order();row=next(csv.DictReader(io.StringIO(self.records.export('items').decode('utf-8-sig'))));self.assertEqual(row['product_name'],"'=EVIL()");self.assertEqual(row['line_total'],'100.00');self.assertEqual(row['quantity'],'2');self.assertEqual(row['design_revision'],'v6')
    def test_supplier_invoices_are_linked_and_duplicates_rejected(self):
        o=self.order();invoice={'supplier':'Maker','reference':'INV-01','amountCents':8080,'currency':'USD','date':'2026-10-14','note':'Two sets'}
        self.records.expense(o['request_id'],invoice)
        with self.assertRaises(HTTPException):self.records.expense(o['request_id'],invoice)
        row=next(csv.DictReader(io.StringIO(self.records.export('expenses').decode('utf-8-sig'))));self.assertEqual(row['amount'],'80.80');self.assertEqual(row['invoice_reference'],'INV-01')
    def test_bad_cursors_filters_and_amounts_rejected(self):
        for kwargs in [{'cursor':'junk'},{'status':'secret'},{'limit':101},{'start':300,'end':100},{'search':None},{'view':[]}]:
            with self.assertRaises(HTTPException):self.records.page(**kwargs)

class SquareReportTests(unittest.TestCase):
    def test_multiple_tenders_refunds_and_actual_fees_are_recorded(self):
        square=Square('test','location','sandbox')
        order={'id':'o','location_id':'location','total_money':{'amount':1000,'currency':'USD'},'total_tax_money':{'amount':0,'currency':'USD'},'tenders':[{'payment_id':'p1'},{'payment_id':'p2'}]}
        payments={p:{'order_id':'o','location_id':'location','status':'COMPLETED','amount_money':{'amount':500,'currency':'USD'},'processing_fee':[{'amount_money':{'amount':30,'currency':'USD'}}],'created_at':'2026-10-14T00:00:00Z'} for p in ['p1','p2']}
        square.request=lambda method,path: {'order':order} if '/orders/' in path else {'payment':payments[path.rsplit('/',1)[1]]}
        report=square.payment_report('o',1000);self.assertTrue(report['fullyPaid']);self.assertEqual(report['fees'],60)
        payments['p1']['refunded_money']={'amount':200,'currency':'USD'};report=square.payment_report('o',1000);self.assertFalse(report['fullyPaid']);self.assertEqual(report['status'],'partially-refunded');self.assertEqual(report['captured'],1000);self.assertEqual(report['refunded'],200)
