"""Email-associated $0 download orders, separate from payments and fulfillment."""
import hashlib
import json
from pathlib import PurePosixPath
import re
import secrets
import time
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import HTTPException
from .newsletter import CONSENT
from .newsletter_mail import email_address


def public_download_url(value):
    try:
        url = urlsplit(value)
        return value if url.scheme == 'https' and url.hostname and not url.username and not url.password and not re.search(r'(^|\.)(github\.com|githubusercontent\.com|github\.io)$', url.hostname, re.I) else ''
    except (ValueError, TypeError):
        return ''


class FreeDownloads:
    def __init__(self, connect, catalog, public_url, beta_asset=None, private_file=None):
        self.connect, self.catalog, self.public_url = connect, catalog, public_url
        self.beta_asset, self.private_file = beta_asset, private_file

    def create(self, body):
        email = email_address(body.get('email'))
        consent = body.get('newsletterConsent', False)
        if type(consent) is not bool:
            raise HTTPException(400, 'Choose whether you want occasional email updates.')
        first_name = body.get('firstName', '')
        if not isinstance(first_name, str) or len(first_name) > 80 or any(ord(c) < 32 for c in first_name) or body.get('company'):
            raise HTTPException(400, 'Check your download details.')
        try:
            reference = str(UUID(body.get('requestId', ''), version=4))
            if reference != body.get('requestId'):
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(400, 'Start a new download request.') from None
        product = next((p for p in self.catalog()['products'] if p['id'] == body.get('productId')), None)
        beta = bool(product and product.get('betaAccess') is True)
        if not product or not product.get('active') or product.get('status') not in ({'available', 'coming-soon'} if beta else {'available'}) or product.get('type') != 'digital' or type(product.get('price')) not in {int, float} or product['price'] != 0 or product.get('pricePending') or product.get('trackStock', True):
            raise HTTPException(409, 'This item is not available as a free download.')
        choices = {product.get('downloadUrl'): product.get('downloadLabel') or 'Free download'}
        for edition in product.get('videoEditions', []):
            for file in edition.get('downloads', []):
                choices[file.get('url')] = edition.get('name', '') + ' · ' + file.get('label', 'Download')
        target = body.get('downloadUrl')
        if beta:
            edition_id = body.get('editionId')
            edition = next((e for e in product.get('softwareEditions', []) if e.get('id') == edition_id and e.get('downloadable') is True), None)
            if not edition or not self.beta_asset:
                raise HTTPException(400, 'Choose an available alpha edition.')
            # Codes and release paths are server-owned. Neither enters the public catalog.
            asset = self.beta_asset(product['id'], edition_id, body.get('testerCode'))
            item = {**asset, 'id': product['id'], 'name': product['name'], 'qty': 1, 'cents': 0,
                    'kind': 'free-digital', 'label': edition['name'] + ' · Alpha', 'beta': True,
                    'editionId': edition_id}
            cart = json.dumps([{'id': product['id'], 'editionId': edition_id}], sort_keys=True)
        else:
            if not isinstance(target, str) or target not in choices or not public_download_url(target):
                raise HTTPException(400, 'Choose a download listed on this product.')
            cart = json.dumps([{'id': product['id'], 'downloadUrl': target}], sort_keys=True)
            item = {'id': product['id'], 'name': product['name'], 'qty': 1, 'cents': 0, 'kind': 'free-digital',
                    'label': choices[target], 'download_url': target,
                    'file': PurePosixPath(urlsplit(target).path).name or 'download'}
        now = int(time.time())
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO orders(request_id,session,cart,items,amount,created,address) VALUES(?,?,?,?,0,?,?)',
                       (reference, secrets.token_urlsafe(32), cart, json.dumps([item]), now,
                        json.dumps({'email': email, 'first_name': first_name.strip(), 'newsletter_consent': consent})))
            order = dict(db.execute('SELECT * FROM orders WHERE request_id=?', (reference,)).fetchone())
            if order['amount'] != 0 or order['cart'] != cart or json.loads(order['address'] or '{}').get('email') != email:
                raise HTTPException(409, 'This download reference belongs to another request. Start again.')
            if consent:
                # Match the existing newsletter's explicit opt-in and suppression rules.
                db.execute('INSERT OR IGNORE INTO newsletter_subscribers(email,created,updated,consent,source) VALUES(?,?,?,?,?)',
                           (email, now, now, CONSENT, 'free-download'))
        # A retry returns another ticket for the same $0 order, never another order.
        return {**self.issue(order, json.loads(order['items'])[0]), 'orderReference': 'RODDY-' + reference}

    def issue(self, order, item, lifetime=7 * 86400):
        if order['amount'] != 0 or item.get('kind') != 'free-digital':
            raise HTTPException(409, 'This is not a free download order.')
        if item.get('beta') is True and self.private_file:
            self.private_file(item)
        elif not public_download_url(item.get('download_url')):
            raise HTTPException(409, 'This is not a free download order.')
        ticket, now = secrets.token_urlsafe(32), int(time.time())
        with self.connect() as db:
            db.execute('DELETE FROM free_download_tickets WHERE expires<?', (now,))
            db.execute('INSERT INTO free_download_tickets(digest,session,product,expires) VALUES(?,?,?,?)',
                       (hashlib.sha256(ticket.encode()).hexdigest(), order['session'], item['id'], now + lifetime))
        return {'name': item['name'], 'filename': item['file'], 'url': self.public_url + '/free-download/' + ticket, 'expiresAt': now + lifetime}

    def redeem(self, ticket):
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', ticket):
            raise HTTPException(404, 'Download not found.')
        digest, now = hashlib.sha256(ticket.encode()).hexdigest(), int(time.time())
        with self.connect() as db:
            row = db.execute('SELECT o.session,o.items,o.amount,t.product FROM free_download_tickets t JOIN orders o ON o.session=t.session WHERE t.digest=? AND t.expires>?', (digest, now)).fetchone()
            if not row:
                raise HTTPException(410, 'This link has expired. Get a new free download from the product page.')
            item = next((i for i in json.loads(row['items']) if i['id'] == row['product'] and i.get('kind') == 'free-digital'), None)
            target = ''
            if item and row['amount'] == 0:
                if item.get('beta') is True and self.private_file:
                    target = item
                else:
                    target = public_download_url(item.get('download_url'))
            if not target:
                raise HTTPException(404, 'Download not found.')
            if isinstance(target, dict):
                self.private_file(target)
            db.execute('UPDATE free_download_tickets SET started=COALESCE(started,?) WHERE digest=?', (now, digest))
            db.execute('INSERT OR IGNORE INTO free_download_receipts(session,started) VALUES(?,?)', (row['session'], now))
        return target
