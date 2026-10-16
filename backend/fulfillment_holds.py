"""Supplier-neutral purchase suspensions. Reasons and costs stay owner-only."""
import time
from fastapi import HTTPException

class FulfillmentHolds:
    def __init__(self,connect):
        self.connect=connect
        with connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS fulfillment_holds(product TEXT PRIMARY KEY, provider TEXT NOT NULL, reason TEXT NOT NULL, created INTEGER NOT NULL)')

    def list(self):
        with self.connect() as db:return [dict(r) for r in db.execute('SELECT * FROM fulfillment_holds ORDER BY created DESC')]

    def suspend(self,items,reason):
        with self.connect() as db:
            for item in items:
                db.execute('INSERT INTO fulfillment_holds VALUES(?,?,?,?) ON CONFLICT(product) DO UPDATE SET reason=excluded.reason,provider=excluded.provider',
                           (item['id'],item.get('kind') or item.get('supplier',{}).get('provider','supplier'),reason,int(time.time())))

    def check(self,items):
        held={r['product'] for r in self.list()}
        if any(i['id'] in held for i in items):
            raise HTTPException(409,'An item is temporarily unavailable while its price is reviewed. Remove it from your cart or try again later.')

    def clear(self,product):
        with self.connect() as db:db.execute('DELETE FROM fulfillment_holds WHERE product=?',(product,))
