from pathlib import Path
import json,html
PROJECT=Path(__file__).resolve().parents[1]
ROOT=PROJECT/'src/keycap-artwork/retro-x'
ROOT.mkdir(parents=True,exist_ok=True)
DARK='#0A0D12'
def path(points):
 return 'M'+'L'.join(f'{x:g} {y:g}' for x,y in points)+'Z'
def clip(points,axis,bound,lower):
 out=[]
 if not points:return out
 for a,b in zip(points[-1:]+points[:-1],points):
  ina=a[axis]>=bound if lower else a[axis]<=bound
  inb=b[axis]>=bound if lower else b[axis]<=bound
  if ina!=inb:
   t=(bound-a[axis])/(b[axis]-a[axis]);c=[a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])];c[axis]=bound;out.append(c)
  if inb:out.append(b)
 return out
def band(poly,y0,y1):return clip(clip(poly,1,y0,True),1,y1,False)
outer=[[2,6],[22,6],[32,19],[42,6],[62,6],[44,32],[60,58],[40,58],[32,46],[24,58],[4,58],[20,32]]
inner=[[6,8],[21,8],[32,23],[43,8],[58,8],[40.5,32],[56.5,56],[41,56],[32,42],[23,56],[7.5,56],[24.5,32]]
colors=['#0877E8','#8050BD','#E91A70','#F7212B','#FF7617','#FFD42A','#56B449']
smooth=[{'path':path(outer),'fill':DARK}]
for i,color in enumerate(colors):
 p=band(inner,8+i*48/7+.8,8+(i+1)*48/7-.8)
 smooth.append({'path':path(p),'fill':color})
# Quantized rows build the silhouette from actual pixel cells, never a raster.
pixel_outer=[]
for row in range(14):
 y=4+row*4
 d=min(row,13-row)
 left=2+d*3;right=62-d*3
 # Four wings meet through a narrow waist, with a notch at the top/bottom.
 left_end=min(30,18+d*3);right_start=max(34,46-d*3)
 if d>=5:pixel_outer.append([[left,y],[right,y],[right,y+4],[left,y+4]])
 else:
  pixel_outer.extend([[[left,y],[left_end,y],[left_end,y+4],[left,y+4]],[[right_start,y],[right,y],[right,y+4],[right_start,y+4]]])
pixel=[{'path':''.join(path(p) for p in pixel_outer),'fill':DARK}]
pixel_colors=['#168A45','#FFD722','#FF9300','#F2252F','#E60078','#7750B6','#00A2E8']
for i,color in enumerate(pixel_colors):
 polys=[]
 for row in [i*2,i*2+1]:
  d=min(row,13-row);y=4+row*4;left=2+d*3;right=62-d*3;left_end=min(30,18+d*3);right_start=max(34,46-d*3)
  y0=y+(1.6 if row%2==0 else 0);y1=y+4-(1.6 if row%2 else 0)
  if d>=5:polys.append([[left+2,y0],[right-2,y0],[right-2,y1],[left+2,y1]])
  else:
   if left_end-left>4:polys.append([[left+2,y0],[left_end-2,y0],[left_end-2,y1],[left+2,y1]])
   if right-right_start>4:polys.append([[right_start+2,y0],[right-2,y0],[right-2,y1],[right_start+2,y1]])
 pixel.append({'path':''.join(path(p) for p in polys),'fill':color})
# Red slab-terminal letterform with an offset cut: original microcomputer X.
red_outer=[[4,6],[25,6],[25,11],[21,11],[32,24],[43,11],[39,11],[39,6],[60,6],[60,12],[55,12],[40,31],[55,51],[60,51],[60,58],[39,58],[39,53],[43,53],[32,40],[21,53],[25,53],[25,58],[4,58],[4,51],[9,51],[24,31],[9,12],[4,12]]
red=[{'path':path(red_outer),'fill':'#D92332'},
     {'path':path([[10,6],[22,6],[22,8],[10,8]])+path([[42,56],[54,56],[54,58],[42,58]]),'fill':'#8D1523'}]
# Eight fully outlined horizontal bars, with broad slab terminals.
mainframe=[[3,4],[26,4],[26,10],[22,10],[32,24],[42,10],[38,10],[38,4],[61,4],[61,10],[56,10],[40,31],[57,52],[61,52],[61,58],[38,58],[38,52],[43,52],[32,38],[21,52],[26,52],[26,58],[3,58],[3,52],[7,52],[24,31],[8,10],[3,10]]
striped=[{'path':''.join(path(band(mainframe,4+i*7,8.4+i*7)) for i in range(8)),'fill':'#244D96'}]
# Opposed red and blue ribbons; the opposing colors weave across the waist.
pb=[{'path':'M5 5H22L40 32L22 59H5L23 32Z','fill':'#244C94'},
    {'path':'M59 5H42L24 32L42 59H59L41 32Z','fill':'#D82C3D'},
    {'path':path([[24,32],[29.3,24],[40,32],[34.7,40]]),'fill':'#244C94'}]
marks={
 'rainbow-x':{'label':'Rainbow X','inspiration':'Macintosh inspired','shapes':smooth},
 'pixel-rainbow-x':{'label':'Pixel rainbow X','inspiration':'Macintosh inspired · pixel variant','shapes':pixel},
 'tandy-x':{'label':'Micro red X','inspiration':'Tandy inspired','shapes':red},
 'ibm-x':{'label':'Mainframe X','inspiration':'IBM inspired · eight bars','shapes':striped},
 'packard-bell-x':{'label':'Twin ribbon X','inspiration':'Packard Bell inspired','shapes':pb},
}
(PROJECT/'src/keycap-artwork/retro-x-marks.json').write_text(json.dumps(marks,indent=2)+'\n')
for ident,m in marks.items():
 art=''.join(f'<path d="{s["path"]}" fill="{s["fill"]}"/>' for s in m['shapes'])
 (ROOT/(ident+'.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><title>RODDY {html.escape(m["label"])} — {html.escape(m["inspiration"])}</title>{art}</svg>\n')
parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="820" viewBox="0 0 1600 820"><rect width="1600" height="820" fill="#F7F7F5"/><g font-family="Arial,sans-serif" fill="#0A0D12"><text x="48" y="62" font-size="15" letter-spacing="3">RODDY / RETRO X COLLECTION</text><text x="48" y="126" font-size="46" font-weight="bold">FIVE SIGNALS FROM ANOTHER ERA.</text><text x="48" y="166" font-size="18">Original X marks · native vectors · your smooth and pixel rainbow references</text>']
for i,(ident,m) in enumerate(marks.items()):
 x=48+i*306
 art=''.join(f'<path d="{s["path"]}" fill="{s["fill"]}"/>' for s in m['shapes'])
 parts.append(f'<rect x="{x}" y="216" width="280" height="470" rx="12" fill="#ECEDE9"/><text x="{x+20}" y="252" font-size="13">0{i+1}</text><rect x="{x+28}" y="282" width="224" height="224" rx="18" fill="#F7F7F5"/><svg x="{x+53}" y="307" width="174" height="174" viewBox="0 0 64 64">{art}</svg><text x="{x+20}" y="548" font-size="20" font-weight="bold">{html.escape(m["label"])}</text><text x="{x+20}" y="577" font-size="12">{html.escape(m["inspiration"])}</text><rect x="{x+20}" y="610" width="96" height="56" rx="7" fill="#7FAFD3"/><svg x="{x+36}" y="614" width="64" height="48" viewBox="0 0 64 64">{art}</svg>')
parts.append('<path d="M48 736H1552" stroke="#C32D28" stroke-width="3"/><text x="48" y="778" font-size="16">RODDY originals inspired by retro computer graphics. Keycap preview on off-white and v6 blue.</text></g></svg>')
(ROOT/'COMPARE_RETRO_X.svg').write_text(''.join(parts))
print('Created five native X designs and an SVG comparison.')
