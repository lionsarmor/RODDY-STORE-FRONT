"""Update Twin Ribbon display artwork and optional private order recipes."""
import argparse,copy,hashlib,json,re
from pathlib import Path
from twin_ribbon import SHAPES

ROOT=Path(__file__).resolve().parents[1]

def mapped(path):
    # Native 64-unit artwork, centered in the existing Commander print area.
    index=0
    def number(match):
        nonlocal index
        value=(float(match[0])-32)*8.7489063867+[627.6246569,426.50916758][index%2]
        index+=1
        return f'{value:.8f}'
    return re.sub(r'-?\d+(?:\.\d+)?',number,path)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--recipes',nargs=2,metavar=('INPUT','OUTPUT'));args=parser.parse_args()
    shapes=[{**s,'path':mapped(s['path'])} for s in SHAPES]
    source=ROOT/'src/keycap-artwork/retro-x-marks.json';marks=json.loads(source.read_text());marks['packard-bell-x']['shapes']=[{k:s[k] for k in ['path','fill']} for s in SHAPES];source.write_text(json.dumps(marks,indent=2,ensure_ascii=False)+'\n')
    svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><title>RODDY Twin Ribbon X</title>'+''.join(f'<path d="{s["path"]}" fill="{s["fill"]}"/>' for s in SHAPES)+'</svg>\n'
    target=ROOT/'src/keycap-artwork/retro-x/packard-bell-x.svg';target.parent.mkdir(exist_ok=True);target.write_text(svg)
    for name,revision in [('x16-v06-cherry-tkl','v06.10-twin-ribbon'),('standard-cherry-tkl','standard-v1.2-twin-ribbon')]:
        p=ROOT/'src/keycap-previews'/(name+'.json');template=json.loads(p.read_text());template['marks']['packard-bell-x']=shapes;template['revision']=revision;p.write_text(json.dumps(template,separators=(',',':'))+'\n')
        if args.recipes:
            source,output=map(Path,args.recipes);recipe=json.loads((source/(name+'.json')).read_text());prototype=recipe['marks']['commander-x16'][0];layers=[]
            for shape in shapes:
                layer=copy.deepcopy(prototype);layer.update(id=hashlib.sha256(('twin-ribbon:'+shape['path']).encode()).hexdigest()[:8],colorId=shape['paletteId'],vectDef=shape['path']);layers.append(layer)
            recipe['marks']['packard-bell-x']=layers;recipe['revision']=revision;recipe['catalogRevision']=revision;output.mkdir(parents=True,exist_ok=True);p=output/(name+'.json');p.write_text(json.dumps(recipe,separators=(',',':'))+'\n');p.chmod(0o600)

if __name__=='__main__':main()
