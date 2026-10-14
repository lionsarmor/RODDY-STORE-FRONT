"""Build evenly spaced, three-character number-row color labels.

Requires fontTools and Liberation Mono Bold. Only display geometry is
written; supplier IDs and manufacturing layouts remain private.
"""
import json
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.svgLib.path import parse_path

root = Path(__file__).resolve().parents[1]
font = TTFont('/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf')
glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
units = 1000 / 19.05
names = [('BLACK', 'ORANGE'), ('WHITE', 'BROWN'), ('RED', 'LIGHT RED'),
         ('CYAN', 'GRAY 1'), ('PURPLE', 'GRAY 2'), ('GREEN', 'LIGHT GREEN'),
         ('BLUE', 'LIGHT BLUE'), ('YELLOW', 'GRAY 3')]
short_names = [('BLK', 'ORG'), ('WHT', 'BRN'), ('RED', 'LRD'), ('CYN', 'GR1'),
               ('PUR', 'GR2'), ('GRN', 'LGN'), ('BLU', 'LBL'), ('YEL', 'GR3')]

def bounds(path):
    pen = BoundsPen(None)
    parse_path(path, pen)
    return pen.bounds

def word_path(word):
    pen, x = SVGPathPen(glyphs), 0
    for char in word:
        name = cmap[ord(char)]
        glyphs[name].draw(TransformPen(pen, (1, 0, 0, -1, x, 0)))
        x += glyphs[name].width
    return pen.getCommands()

cap = bounds(word_path('H'))
scale = 1.15 * units / (cap[3] - cap[1])
baseline = 583.732 - (cap[1] + cap[3]) / 2 * scale
cell_width = glyphs[cmap[ord('H')]].width
def label_path(text, center_x):
    assert len(text) == 3 and ' ' not in text
    assert all(glyphs[cmap[ord(char)]].width == cell_width for char in text)
    advance = 3 * cell_width * scale
    assert advance < 3.5 * units
    pen = SVGPathPen(None)
    parse_path(word_path(text), TransformPen(pen, (scale, 0, 0, scale,
               center_x - advance / 2, baseline)))
    return pen.getCommands()

preview = json.loads((root/'src/keycap-previews/x16-v06-cherry-tkl.json').read_text())
labels = {}
for index, names_for_key in enumerate(names, 1):
    key = next(k for k in preview['keys'] if k['id'] == str(index))
    # Each combined legend has top glyphs followed by two lower square frames.
    import re
    subpaths = re.findall(r'[Mm][^Mm]*', key['shapes'][0]['path'])
    top, frames = [], []
    for subpath in subpaths:
        b = bounds(subpath)
        if b[1] >= 500:
            frames.append(subpath)
        else:
            assert b[3] < 400, 'Unexpected number-row geometry'
            top.append(subpath)
    assert len(frames) == 4 and top
    shapes = [{**key['shapes'][0], 'path': ''.join(top)}]
    for text, cx in zip(short_names[index-1], [380.977, 595.938]):
        path = label_path(text, cx)
        b = bounds(path)
        assert 280 < b[0] and b[2] < 700 and 480 < b[1] and b[3] < 680
        shapes.append({'path': path, 'fill': '#262626', 'paletteId': 'GR001', 'inkRole': 'auto'})
    labels[str(index)] = {'names': list(names_for_key), 'labels': list(short_names[index-1]), 'shapes': shapes}
(root/'src/keycap-artwork/number-row-labels.json').write_text(json.dumps({
    'font': 'Liberation Mono Bold', 'capHeightMm': 1.15,
    'baseline': baseline, 'characterCount': 3, 'labelAdvance': 3 * cell_width * scale,
    'source': 'Original v6 COLOR_PALETTE.csv color names', 'keys': labels
}, separators=(',', ':')) + '\n')
print('Outlined 16 color names; retained top number and shifted-symbol glyphs; removed all box frames.')
