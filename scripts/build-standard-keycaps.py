"""Build display-only standard ANSI legends for the existing 87-key layout."""
import copy,json
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.svgLib.path import parse_path
root=Path(__file__).resolve().parents[1];font=TTFont('/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf');glyphs=font.getGlyphSet();cmap=font.getBestCmap();units=1000/19.05
cap_pen=BoundsPen(glyphs);glyphs[cmap[ord('H')]].draw(cap_pen);cap_height=cap_pen.bounds[3]-cap_pen.bounds[1]

def bounds(path):
 p=BoundsPen(None);parse_path(path,p);return p.bounds

def text(text,cx,cy,height=2.1,max_width=8):
 p=SVGPathPen(glyphs);x=0
 for char in text:
  name=cmap[ord(char)];glyphs[name].draw(TransformPen(p,(1,0,0,-1,x,0)));x+=glyphs[name].width
 path=p.getCommands();a,b,c,d=bounds(path);scale=min(height*units/cap_height,max_width*units/(c-a));p=SVGPathPen(None);parse_path(path,TransformPen(p,(scale,0,0,scale,cx-(a+c)/2*scale,cy-(b+d)/2*scale)))
 return {'path':p.getCommands(),'fill':'#262626','paletteId':'GR001','inkRole':'auto'}

preview=copy.deepcopy(json.loads((root/'src/keycap-previews/x16-v06-cherry-tkl.json').read_text()))
preview.update(id='standard-cherry-tkl',name='Standard ANSI 87 · Cherry',revision='standard-v1',numberRows=['plain'],compatibility='ANSI 87-key TKL · Cherry profile · MX stems · 6.25u spacebar')
pairs={'special':('~','`'),'1':('!','1'),'2':('@','2'),'3':('#','3'),'4':('$','4'),'5':('%','5'),'6':('^','6'),'7':('&','7'),'8':('*','8'),'9':('(','9'),'0':(')','0'),'minus':('_','-'),'equals':('+','='),'lbracket':('{','['),'rbracket':('}',']'),'backslash':('|','\\'),'semicolon':(':',';'),'quote':('"',"'"),'comma':('<',','),'period':('>','.'),'slash':('?','/')}
names={'shift-lock':'Caps Lock','return':'Enter','lshift':'Shift','rshift':'Shift','lctrl':'Ctrl','rctrl':'Ctrl','lalt':'Alt','ralt':'Alt','fn':'Fn','menu':'Menu','backspace':'Backspace','tab':'Tab','restore':'Print Scr','display':'Scroll Lock','run-stop':'Pause','inst':'Insert','clr-home':'Home','page-up':'Page Up','del':'Delete','end':'End','page-dn':'Page Down','esc':'Esc'}
for key in preview['keys']:
 for field in ['numberRowText','colorNames','colorLabels']:key.pop(field,None)
 ident=key['id'];cx=(key['width']+64)/2
 if ident in {'up','left','down','right','commander'}:continue
 if ident=='space':key['shapes']=[];continue
 if ident in pairs:key['shapes']=[text(pairs[ident][0],cx,330,2),text(pairs[ident][1],cx,640,2)]
 else:
  label=names.get(ident,ident.upper());key['name']=label
  if key['width']<=936 and ' ' in label:
   key['shapes']=[text(word,cx,380+i*190,1.7,max_width=9) for i,word in enumerate(label.split(' '))]
  else:key['shapes']=[text(label,cx,475,2.7 if len(label)==1 else 2,max_width=key['width']/units-8.5)]
preview['keys'][next(i for i,k in enumerate(preview['keys']) if k['id']=='commander')]['name']='System key'
(root/'src/keycap-previews/standard-cherry-tkl.json').write_text(json.dumps(preview,separators=(',',':'),ensure_ascii=False)+'\n')
print('Built 87 standard keys with normal ANSI legends; retained the existing layout and symbol/arrow options.')
