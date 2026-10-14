"""Build stock-color rainbow bands inside the existing v6 Commander silhouette.

Updates display geometry only. Optional --recipes INPUT OUTPUT updates private
recipes outside the public tree, preserving every existing design and default.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def polygons(path):
    tokens = iter(re.findall(r'[MLHVZ]|-?\d+(?:\.\d+)?', path))
    result, points = [], []
    x = y = 0
    for command in tokens:
        if command in ('M', 'L'):
            x, y = float(next(tokens)), float(next(tokens))
        elif command == 'H':
            x = float(next(tokens))
        elif command == 'V':
            y = float(next(tokens))
        elif command == 'Z':
            result.append(points)
            points = []
            continue
        else:
            raise ValueError('Unexpected Commander silhouette command: '+command)
        points.append((x, y))
    return result


def clip(points, boundary, above):
    output = []
    for a, b in zip(points, points[1:]+points[:1]):
        inside_a = a[1] >= boundary if above else a[1] <= boundary
        inside_b = b[1] >= boundary if above else b[1] <= boundary
        if inside_a:
            output.append(a)
        if inside_a != inside_b:
            t = (boundary-a[1])/(b[1]-a[1])
            output.append((a[0]+t*(b[0]-a[0]), boundary))
    return output


def rainbow(template):
    palette = json.loads((ROOT/'backend/keycap_palette.json').read_text())['colors']
    def rgb(value):
        return tuple(int(value[i:i+2], 16) for i in (1, 3, 5))
    # Top-to-bottom order of the Commander rainbow, quantized to stock inks.
    targets = ['#A779AA', '#775BA2', '#565CA7', '#357BBE', '#419FC5',
               '#56BAC4', '#64B894', '#91BE57', '#D2C347', '#F5C744',
               '#F7AE42', '#F18B42', '#E96341', '#DF424B']
    outline = polygons(template['marks']['commander-x16'][0]['path'])
    lo = min(y for p in outline for _, y in p)
    hi = max(y for p in outline for _, y in p)
    shapes = []
    for index, target in enumerate(targets):
        color = min(palette, key=lambda c: sum((a-b)**2 for a, b in zip(rgb(target), rgb(c['hex']))))
        bottom, top = lo+(hi-lo)*index/len(targets), lo+(hi-lo)*(index+1)/len(targets)
        paths = []
        for polygon in outline:
            points = clip(clip(polygon, bottom, True), top, False)
            if len(points) >= 3:
                paths.append('M'+'L'.join(f'{x:.8f} {y:.8f}' for x, y in points)+'Z')
        shapes.append({'path': ''.join(paths), 'fill': color['hex'], 'paletteId': color['id']})
    return shapes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipes', nargs=2, metavar=('INPUT', 'OUTPUT'))
    args = parser.parse_args()
    for name, revision in [('x16-v06-cherry-tkl', 'v06.9-commander-options'),
                           ('standard-cherry-tkl', 'standard-v1.1-commander-options')]:
        path = ROOT/'src/keycap-previews'/(name+'.json')
        template = json.loads(path.read_text())
        shapes = rainbow(template)
        template['marks']['commander-x16-rainbow'] = shapes
        template['marks']['blank'] = []
        template['revision'] = revision
        path.write_text(json.dumps(template, separators=(',', ':'))+'\n')
        if args.recipes:
            source, output = map(Path, args.recipes)
            recipe = json.loads((source/(name+'.json')).read_text())
            prototype = recipe['marks']['commander-x16'][0]
            recipe['marks']['commander-x16-rainbow'] = []
            for shape in shapes:
                layer = copy.deepcopy(prototype)
                layer_id = hashlib.sha256(('commander-rainbow:'+shape['path']).encode()).hexdigest()[:8]
                layer.update(id=layer_id, colorId=shape['paletteId'], vectDef=shape['path'])
                recipe['marks']['commander-x16-rainbow'].append(layer)
            recipe['marks']['blank'] = []
            recipe['revision'] = revision
            output.mkdir(parents=True, exist_ok=True)
            target = output/(name+'.json')
            target.write_text(json.dumps(recipe, separators=(',', ':'))+'\n')
            target.chmod(0o600)


if __name__ == '__main__':
    main()
