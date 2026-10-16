#!/usr/bin/env python3
"""Publish a native Weather Commander release ZIP into the local storefront."""
import hashlib,json,re,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'.tools/customer-docs/source/WEATHERCMD.zip'
catalog=json.loads((ROOT/'public/data/products.json').read_text())
products=catalog if isinstance(catalog,list) else catalog['products']
product=next(p for p in products if p['id']=='weather-commander-x16')
version=product['specs']['Version']
assert re.fullmatch(r'\d+\.\d+\.\d+',version)
name=f'WEATHERCMD-v{version}.zip'
assert product['downloadUrl']==f'https://roddy.world/downloads/software/{name}'
with zipfile.ZipFile(source) as archive:
    assert archive.testzip() is None
    entries={info.filename:archive.read(info) for info in archive.infolist()}
    assert len(entries)==len(archive.infolist()),'Duplicate archive entries'
assert len(entries)==71,'Expected 69 runtime files and two text guides'
for path in entries:
    assert re.fullmatch(r'WEATHERCMD/(?:[A-Z0-9]{1,12}\.(?:PRG|BIN)|START-HERE.TXT|DATA-NOTICE.TXT)',path),path
    assert Path(path).name not in {'WCSETUP.BIN','WCDATA.BIN','WCRLIVE.BIN','WCQUERY.BIN','WCCITIES.BIN','WCRPNG.BIN'},path
assert 'WEATHERCMD/WEATHER.PRG' in entries
start=entries['WEATHERCMD/START-HERE.TXT'].decode()
assert start.startswith(f'WEATHER COMMANDER {version} -'), 'Source release and storefront version differ'
start=start.replace('https://github.com/lionsarmor/WEATHER-COMMANDER/releases','https://roddy.world/#/product/weather-commander-x16').replace('https://github.com/lionsarmor/WEATHER-COMMANDER','https://roddy.world/downloads/docs/weather-commander-guide.pdf')
entries['WEATHERCMD/START-HERE.TXT']=start.encode()
entries['WEATHERCMD/WEATHER_COMMANDER_GUIDE.pdf']=(ROOT/'public/downloads/docs/weather-commander-guide.pdf').read_bytes()
output=ROOT/'public/downloads/software'/name
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
    for path,data in sorted(entries.items()):
        info=zipfile.ZipInfo(path,date_time=(1980,1,1,0,0,0));info.create_system=3
        info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED
        archive.writestr(info,data)
# Update only these two entries; keep all other customer download checksums.
manifest=ROOT/'public/downloads/SHA256SUMS.txt'
checks=dict(line.split(maxsplit=1)[::-1] for line in manifest.read_text().splitlines() if line.strip())
for path in [output,ROOT/'public/downloads/docs/weather-commander-guide.pdf']:
    checks[str(path.relative_to(ROOT/'public/downloads'))]=hashlib.sha256(path.read_bytes()).hexdigest()
manifest.write_text(''.join(f'{digest}  {path}\n' for path,digest in sorted(checks.items())))
print(f'Packaged {output.name}: 69 unchanged PRG/BIN files, guides; no emulator or personal data.')
