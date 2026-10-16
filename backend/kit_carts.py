"""Owner-only reusable kit templates; cart creation never submits an order."""
import hashlib
import json
import time
from fastapi import HTTPException, Request
from .mouser_bom import expected_lines, unit_lines
from .mouser_orders import MouserUnavailable


def register_kit_carts(app, commerce, require_admin):
    with commerce.connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS mouser_kit_carts(
            cart TEXT PRIMARY KEY, product TEXT NOT NULL, revision TEXT NOT NULL,
            signature TEXT NOT NULL, quantity INTEGER NOT NULL, country TEXT NOT NULL,
            lines TEXT NOT NULL, created INTEGER NOT NULL)''')

    @app.get('/admin/kit-carts')
    def read(request: Request):
        require_admin(request)
        with commerce.connect() as db:
            rows = [dict(r) for r in db.execute('SELECT * FROM mouser_kit_carts ORDER BY created DESC LIMIT 50')]
        for row in rows:
            row['lines'] = json.loads(row['lines'])
        return {'carts': rows}

    @app.post('/admin/kit-carts')
    def create(request: Request, body: dict):
        require_admin(request)
        product = next((p for p in commerce.catalog()['products'] if p['id'] == body.get('productId')), None)
        quantity, country = body.get('quantity', 1), body.get('country', 'US')
        if type(quantity) is not int or not 1 <= quantity <= 99 or country not in {'US', 'CA'}:
            raise HTTPException(400, 'Choose 1–99 kits and a supported shipping country.')
        supplier = (product or {}).get('supplier') or {}
        if not supplier.get('bom'):
            raise HTTPException(400, 'Choose a published Mouser parts-kit template.')
        if country not in product.get('shippingCountries', ['US', 'CA']):
            raise HTTPException(400, 'This kit is not sourced for that country.')
        try:
            unit_lines(supplier)
            items = [{'supplier': supplier, 'qty': quantity}]
            lines = dict(expected_lines(items))
            # A fresh API cart, not the website's Share Access ID. No order call.
            cart = commerce.mouser_factory().create_cart(items, country)
        except (ValueError, MouserUnavailable) as e:
            raise HTTPException(409, str(e)) from None
        signature = hashlib.sha256(json.dumps(supplier['bom'], sort_keys=True).encode()).hexdigest()
        row = {'cart': cart, 'product': product['id'], 'revision': supplier['bom']['revision'],
               'signature': signature, 'quantity': quantity, 'country': country,
               'lines': lines, 'created': int(time.time())}
        with commerce.connect() as db:
            db.execute('INSERT INTO mouser_kit_carts VALUES(?,?,?,?,?,?,?,?)',
                       (cart, row['product'], row['revision'], signature, quantity, country, json.dumps(lines), row['created']))
        return {'cart': row, 'message': 'Fresh cart saved. No order was placed. Stock, destination shipping and pricing are checked at checkout.'}
