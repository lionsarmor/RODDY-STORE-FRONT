"""Build outlined number-row color labels in the existing navigation font.

Requires fontTools and Liberation Sans Narrow Bold. Only display geometry is
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
font = TTFont('/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf')
glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
units = 1000 / 19.05
names = [('BLACK', 'ORANGE'), ('WHITE', 'BROWN'), ('RED', 'LIGHT RED'),
         ('CYAN', 'GRAY 1'), ('PURPLE', 'GRAY 2'), ('GREEN', 'LIGHT GREEN'),
         ('BLUE', 'LIGHT BLUE'), ('YELLOW', 'GRAY 3')]

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
scale = units / (cap[3] - cap[1])  # 1 mm cap height, with 0.28 mm line gaps.
def label_path(text, center_x):
    lines = text.split(' ')
    height = (len(lines) - 1) * 1.28 * units
    result = []
    for i, line in enumerate(lines):
        path = word_path(line)
        x1, y1, x2, y2 = bounds(path)
        sx = min(scale, 3.5 * units / (x2 - x1))
        cy = 583.732 - height / 2 + i * 1.28 * units
        pen = SVGPathPen(None)
        parse_path(path, TransformPen(pen, (sx, 0, 0, scale,
                   center_x - (x1 + x2) / 2 * sx, cy - (y1 + y2) / 2 * scale)))
        result.append(pen.getCommands())
    return ''.join(result)

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
    for text, cx in zip(names_for_key, [380.977, 595.938]):
        path = label_path(text, cx)
        b = bounds(path)
        assert 280 < b[0] and b[2] < 700 and 480 < b[1] and b[3] < 680
        shapes.append({'path': path, 'fill': '#262626', 'paletteId': 'GR001', 'inkRole': 'auto'})
    labels[str(index)] = {'names': list(names_for_key), 'shapes': shapes}
(root/'src/keycap-artwork/number-row-labels.json').write_text(json.dumps({
    'font': 'Liberation Sans Narrow Bold', 'capHeightMm': 1,
    'source': 'Original v6 COLOR_PALETTE.csv color names', 'keys': labels
}, separators=(',', ':')) + '\n')
print('Outlined 16 color names; retained top number and shifted-symbol glyphs; removed all box frames.')
