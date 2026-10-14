"""Validated keycap recipes and frozen, owner-only manufacturing packets."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import zipfile

from fastapi import HTTPException

TEMPLATES = Path(os.getenv('KEYCAP_TEMPLATES_DIR', '/var/lib/roddy-store/keycap-templates'))
MARKS = {ident: option['label'] for ident, option in json.loads(Path(__file__).with_name('keycap_mark_options.json').read_text()).items() if option.get('enabled', True)}
ARROWS = {'small-black': 'Small black arrows', 'small-white': 'Small white arrows',
          'bold-black': 'Bold black arrows', 'bold-white': 'Bold white arrows'}
FIELDS = {'profileId', 'revision', 'alpha', 'modifiers', 'accents', 'mark', 'arrows', 'keyColors'}
PALETTE_BYTES = Path(__file__).with_name('keycap_palette.json').read_bytes()
PALETTE_DOCUMENT = json.loads(PALETTE_BYTES)
PALETTE = {color['id']: color for color in PALETTE_DOCUMENT['colors']}


def selection_input(raw):
    if not isinstance(raw, dict) or set(raw) != FIELDS or any(not isinstance(raw[k], str) for k in FIELDS - {'keyColors'}):
        raise HTTPException(400, 'Choose your keycap design on the product page.')
    if (any(raw[k] not in PALETTE for k in ['alpha', 'modifiers', 'accents'])
            or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,100}', raw['profileId'])
            or not re.fullmatch(r'[a-zA-Z0-9._-]{1,40}', raw['revision'])
            or raw['mark'] not in MARKS or raw['arrows'] not in ARROWS):
        raise HTTPException(400, 'Invalid keycap color, symbol or arrow style.')
    overrides = raw['keyColors']
    if (not isinstance(overrides, dict) or len(overrides) > 256
            or any(not isinstance(k, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,39}', k)
                   or not isinstance(v, str) or v not in PALETTE for k, v in overrides.items())):
        raise HTTPException(400, 'Choose Yuzu palette colors for your individual keys.')
    return {**{k: raw[k] for k in sorted(FIELDS - {'keyColors'})}, 'keyColors': dict(sorted(overrides.items()))}


def dark(color):
    rgb = [int(color[i:i+2], 16)/255 for i in [1, 3, 5]]
    rgb = [n/12.92 if n <= .04045 else ((n+.055)/1.055)**2.4 for n in rgb]
    return sum(a*b for a, b in zip(rgb, [.2126, .7152, .0722])) < .179


def validate_colors(value):
    """Fail closed if any manufacturing field uses a color outside the palette."""
    used = set()
    def visit(node):
        if isinstance(node, dict):
            for key, child in node.items():
                if key == 'colorId':
                    if not isinstance(child, str) or child not in PALETTE:
                        raise HTTPException(409, 'This keyboard artwork needs a Yuzu palette update.')
                    used.add(child)
                else:
                    visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
    visit(value)
    return used


def snapshot(catalog, product, raw):
    selection = selection_input(raw)
    profiles = catalog.get('keycapProfiles', [])
    profile = next((p for p in profiles if p.get('id') == product['keycaps'].get('profileId')), None)
    if (not profile or selection['profileId'] != profile['id'] or selection['revision'] != profile.get('revision')
            or selection['mark'] not in profile.get('marks', MARKS)
            or selection['arrows'] not in profile.get('arrows', ARROWS)):
        raise HTTPException(409, 'This keyboard profile changed. Refresh your design on the product page.')
    template_id = profile.get('templateId', '')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,100}', template_id):
        raise HTTPException(409, 'This keyboard template is unavailable.')
    try:
        template_bytes = (TEMPLATES / (template_id+'.json')).read_bytes()
        template = json.loads(template_bytes)
    except (OSError, ValueError):
        raise HTTPException(409, 'This keyboard template is unavailable.') from None
    if template.get('paletteVersion') != PALETTE_DOCUMENT['version']:
        raise HTTPException(409, 'This keyboard template needs its Yuzu palette update.')
    key_ids = {meta['keyId'] for meta in template['meta'].values()}
    if any(key not in key_ids for key in selection['keyColors']):
        raise HTTPException(400, 'An individual key does not belong to this keyboard profile.')
    out = copy.deepcopy(template['base'])
    out['name'] = f"RODDY {profile['name']} {selection['mark']} {selection['arrows']}"
    for ident, key in out['keys'].items():
        meta = template['meta'][ident]
        color = selection['keyColors'].get(meta['keyId'], selection[meta['group']])
        key['colorId'] = color
        for index in meta.get('autoLegendLayers', []):
            key['layers'][index]['colorId'] = 'GR002' if dark(PALETTE[color]['hex']) else 'GR001'
        if meta['sourceKey'] == 'COMMANDER':
            key['layers'] = copy.deepcopy(template['marks'][selection['mark']])
        if ident in template['arrows']:
            key['layers'] = copy.deepcopy(template['arrows'][ident] if selection['arrows'].startswith('bold-') else template['base']['keys'][ident]['layers'])
            for layer in key['layers']:
                layer['colorId'] = 'GR002' if selection['arrows'].endswith('-white') else 'GR001'
    used_colors = validate_colors(out)
    encoded = json.dumps(out, sort_keys=True, separators=(',', ':')).encode()
    return {'profile': copy.deepcopy(profile), 'templateId': template_id, 'templateRevision': template['revision'],
            'templateSha256': hashlib.sha256(template_bytes).hexdigest(), 'selection': selection,
            'compatibility': template['compatibility'], 'json': out, 'sha256': hashlib.sha256(encoded).hexdigest(),
            'paletteVersion': PALETTE_DOCUMENT['version'], 'paletteSha256': hashlib.sha256(PALETTE_BYTES).hexdigest(),
            'palette': {ident: {k: PALETTE[ident][k] for k in ['name', 'hex', 'cmyk']} for ident in sorted(used_colors)}}


def label(selection):
    count = len(selection.get('keyColors', {}))
    return (' / '.join(selection[k] for k in ['alpha', 'modifiers', 'accents']) + ' · ' + MARKS[selection['mark']]
            + ' · ' + ARROWS[selection['arrows']] + (f' · {count} individual key colors' if count else ''))


def packet(order):
    """Use only the order snapshot, never the current catalog or recipe files."""
    items = json.loads(order['items']) if isinstance(order['items'], str) else order['items']
    address = json.loads(order['address']) if isinstance(order.get('address'), str) else order.get('address')
    reference = 'RODDY-' + order['request_id']
    summary = {'orderReference': reference, 'squareOrderId': order['provider_id'], 'created': order['created'],
               'currency': 'USD', 'amountPaidCents': order['amount'], 'shippingChargedCents': order['shipping'],
               'delivery': address, 'items': [], 'instructions': 'Manually import each Yuzu JSON, confirm quantity, fit, colors, price and delivery details, then submit to the maker. This packet does not place a supplier order. Do not upload ORDER_DETAILS.json to Yuzu.'}
    files = []
    for index, item in enumerate(items):
        if item.get('kind') != 'keycaps':
            continue
        design = item['designSnapshot']
        filename = f"{index+1:02d}-{item['id']}-{design['sha256'][:12]}-yuzu.json"
        files.append((filename, json.dumps(design['json'], indent=2).encode()+b'\n'))
        summary['items'].append({'productId': item['id'], 'name': item['name'], 'quantity': item['qty'],
                                 'unitPriceCents': item['cents'], 'profile': design['profile'],
                                 'templateId': design['templateId'], 'templateRevision': design['templateRevision'],
                                 'templateSha256': design['templateSha256'], 'designSha256': design['sha256'],
                                 'selection': design['selection'], 'compatibility': design['compatibility'], 'file': filename})
        if 'palette' in design:
            summary['items'][-1].update(paletteVersion=design['paletteVersion'], palette=design['palette'])
    files.append(('ORDER_DETAILS.json', json.dumps(summary, indent=2).encode()+b'\n'))
    return summary, files


def packet_zip(order):
    summary, files = packet(order)
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in files:
            archive.writestr(name, content)
    return data.getvalue()
