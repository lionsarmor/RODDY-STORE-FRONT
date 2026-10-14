"""Outline Delete in the existing navigation font. Requires fonttools.

Writes display geometry only; no supplier identifiers or layouts.
"""
import json
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
font = TTFont('/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf')
glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
scale = 9.4 * .315 * (1000 / 19.05) / font['head'].unitsPerEm
pen, x = SVGPathPen(glyphs), 0
for char in 'Delete':
    name = cmap[ord(char)]
    glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, 0)))
    x += glyphs[name].width * scale
out = Path(__file__).resolve().parents[1] / 'src/keycap-artwork/delete-legend.json'
out.write_text(json.dumps({'text': 'Delete', 'path': pen.getCommands(), 'font': 'Liberation Sans Narrow Bold', 'sizeMm': 9.4 * .315}) + '\n')
