"""Private operational settings; recording an agreement never enables purchases."""
import json
import time
from fastapi import HTTPException, Request
from .newsletter_mail import text

SUPPLIER_DIRECTORY = {
    'mouser': {'name': 'Mouser Electronics', 'website': 'https://www.mouser.com/', 'workflow': 'Automatic or manual ordering · live stock checks', 'services': ['Components', 'Development boards'], 'api': 'Search connected separately. Automatic ordering requires account setup and automatic product fulfillment.'},
    'aliexpress': {'name': 'AliExpress', 'website': 'https://www.aliexpress.com/', 'workflow': 'Manual ordering · exact seller and variant', 'services': ['Finished products', 'Accessories'], 'api': 'Product reads and shipping quotes only. Purchasing remains manual.'},
    'yuzu': {'name': 'Yuzu Keycaps', 'website': 'https://yuzukeycaps.com/', 'workflow': 'Manual ordering · private design JSON', 'services': ['Custom keycaps'], 'api': 'No ordering API connected. Download paid order packets from Orders.'},
    'pcbway': {'name': 'PCBWay', 'website': 'https://www.pcbway.com/', 'workflow': 'Quote and prototype review', 'services': ['Bare PCBs', 'Assembly', 'Firmware programming', 'Functional testing', 'Enclosures / box build', 'Customer dispatch'], 'api': 'Partner approval required. No PCB or assembly ordering API connected.'},
    'printify': {'name': 'Printify', 'website': 'https://printify.com/', 'workflow': 'Automatic production after verified payment', 'services': ['Print on demand'], 'api': 'Manage the existing connection and product mappings in Printify.'},
}
DEFAULT_INSTRUCTIONS = ('Send the purchasing invoice to RODDY electronically. Include a RODDY packing slip if agreed. '
    'Please confirm the selected packaging and paperwork requests before accepting the order.')


def defaults():
    return {'contact': '', 'accountReference': '', 'agreementStatus': 'unconfirmed', 'agreementEvidence': '',
            'packaging': 'neutral', 'omitPriceReceipts': True, 'omitPromotions': True,
            'dispatch': 'confirm-per-order', 'countries': [], 'services': [], 'leadTime': '',
            'minimumOrder': '', 'instructions': DEFAULT_INSTRUCTIONS}


def register_supplier_directory(app, connect, require_admin):
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS supplier_directory (provider TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL, updated INTEGER NOT NULL)')

    def records():
        with connect() as db:
            rows = {r['provider']: r for r in db.execute('SELECT * FROM supplier_directory')}
        return [{**meta, 'provider': provider, 'revision': rows[provider]['revision'] if provider in rows else 0,
                 'updated': rows[provider]['updated'] if provider in rows else None,
                 'settings': {**defaults(), **(json.loads(rows[provider]['data']) if provider in rows else {})}}
                for provider, meta in SUPPLIER_DIRECTORY.items()]

    @app.get('/admin/suppliers/directory')
    def overview(request: Request):
        require_admin(request)
        return {'suppliers': records()}

    @app.post('/admin/suppliers/directory')
    def save(request: Request, body: dict):
        require_admin(request)
        provider = body.get('provider')
        if not isinstance(provider, str) or provider not in SUPPLIER_DIRECTORY:
            raise HTTPException(400, 'Choose a supported supplier.')
        values = body.get('settings')
        if not isinstance(values, dict) or set(values) - set(defaults()):
            raise HTTPException(400, 'Check the supplier settings. API secrets belong in connection settings.')
        clean = defaults()
        for field, maximum in [('contact', 250), ('accountReference', 160), ('agreementEvidence', 1000), ('leadTime', 160), ('minimumOrder', 160), ('instructions', 2500)]:
            clean[field] = text(values.get(field, clean[field]), maximum, field)
        for field, options in [('agreementStatus', ['unconfirmed', 'requested', 'confirmed', 'unavailable']), ('packaging', ['neutral', 'roddy', 'standard']), ('dispatch', ['confirm-per-order', 'customer', 'self'])]:
            if values.get(field) not in options:
                raise HTTPException(400, 'Choose a supported shipping or packaging option.')
            clean[field] = values[field]
        for field in ['omitPriceReceipts', 'omitPromotions']:
            if type(values.get(field)) is not bool:
                raise HTTPException(400, 'Check the paperwork preferences.')
            clean[field] = values[field]
        for field, options in [('countries', ['US', 'CA']), ('services', SUPPLIER_DIRECTORY[provider]['services'])]:
            selected = values.get(field)
            if not isinstance(selected, list) or any(not isinstance(v, str) or v not in options for v in selected) or len(set(selected)) != len(selected):
                raise HTTPException(400, 'Check supported destinations and services.')
            clean[field] = selected
        if clean['agreementStatus'] == 'confirmed' and not clean['agreementEvidence'].strip():
            raise HTTPException(400, 'Record who confirmed the packaging agreement and when.')
        if type(body.get('revision')) is not int:
            raise HTTPException(400, 'Reload supplier settings before saving.')
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT revision FROM supplier_directory WHERE provider=?', (provider,)).fetchone()
            revision = row['revision'] if row else 0
            if revision != body['revision']:
                raise HTTPException(409, 'This supplier changed in another browser. Reload before saving.')
            db.execute('INSERT OR REPLACE INTO supplier_directory VALUES(?,?,?,?)', (provider, revision + 1, json.dumps(clean), int(time.time())))
        return {'suppliers': records(), 'orderPlaced': False}
