"""Keep the X16 display and optional private print recipe geometrically identical.

Usage: python3 scripts/build-number-row-swatches.py [private-template.json]
The optional supplier recipe must remain outside version control.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTWORK_REVISION = 'number-swatches-v2'
CENTERS = (381, 596)
CY, OUTER, BORDER = 584, 184, 14


def square(cx, size, reverse=False):
    x, y = cx-size/2, CY-size/2
    end_x, end_y = x+size, y+size
    if reverse:
        return f'M{x:g} {y:g}V{end_y:g}H{end_x:g}V{y:g}Z'
    return f'M{x:g} {y:g}H{end_x:g}V{end_y:g}H{x:g}Z'


preview_path = ROOT/'src/keycap-previews/x16-v06-cherry-tkl.json'
preview = json.loads(preview_path.read_text())
shapes_by_key = {}
for key in preview['keys']:
    if key['id'] not in tuple(str(n) for n in range(1, 9)):
        continue
    # The text option already stores only the unchanged upper number/symbol.
    top = key['numberRowText'][0]['path']
    frames = ''.join(square(cx, OUTER)+square(cx, OUTER-2*BORDER, True) for cx in CENTERS)
    key['shapes'][0]['path'] = top+frames
    for shape, cx in zip(key['shapes'][1:], CENTERS):
        shape['path'] = square(cx, OUTER-2*BORDER)
    shapes_by_key[key['id']] = key['shapes']
preview['swatchArtworkRevision'] = ARTWORK_REVISION
preview_path.write_text(json.dumps(preview, separators=(',', ':'))+'\n')

if len(sys.argv) > 1:
    path = Path(sys.argv[1])
    template = json.loads(path.read_text())
    changed = 0
    for ident, meta in template['meta'].items():
        if meta['keyId'] not in shapes_by_key:
            continue
        layers = template['base']['keys'][ident]['layers']
        shapes = shapes_by_key[meta['keyId']]
        assert len(layers) == len(shapes) == 3
        for layer, shape in zip(layers, shapes):
            assert layer['colorId'] == shape['paletteId']
            assert layer['x'] == layer['y'] == 0
            assert layer['vectViewbox'] == '0 0 1000 1000' and layer['vectScale'] == 100
            layer['vectDef'] = shape['path']
        changed += 1
    assert changed == 8
    # Choice compatibility stays unchanged; frozen orders retain their old paths.
    template['revision'] = 'v06.13-swatches'
    template['swatchArtworkRevision'] = ARTWORK_REVISION
    path.write_text(json.dumps(template, separators=(',', ':'))+'\n')

print('Updated 16 swatches: equal 156-unit fills, 14-unit borders, 31-unit gap.')
