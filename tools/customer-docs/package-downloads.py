"""Prepare storefront downloads from owner-supplied release files, not private source trees."""
from pathlib import Path
import zipfile,shutil,hashlib,json
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.tools/customer-docs/source'
OUT=ROOT/'public/downloads'
# The runtime stays byte-identical; only the old repository pointers in the quick-start change.
with zipfile.ZipFile(SOURCE/'WEATHERCMD.zip') as src, zipfile.ZipFile(OUT/'software/WEATHERCMD-v0.2.1.zip','w',zipfile.ZIP_DEFLATED) as dst:
 for info in src.infolist():
  data=src.read(info)
  if info.filename.endswith('/START-HERE.TXT'):
   data=data.decode().replace('https://github.com/lionsarmor/WEATHER-COMMANDER/releases','https://roddy.world/#/product/weather-commander-x16').replace('https://github.com/lionsarmor/WEATHER-COMMANDER','https://roddy.world/downloads/docs/weather-commander-guide.pdf').encode()
  dst.writestr(info,data)
 dst.write(OUT/'docs/weather-commander-guide.pdf','WEATHERCMD/WEATHER_COMMANDER_GUIDE.pdf')
shutil.copy2(SOURCE/'Shadow_Over_space.bin',OUT/'software/Shadow_Over_space-v0.1.0.bin')
# Deliberate allowlist: printable shell geometry and a customer PDF, no board CAD,
# purchasing material, build scripts or owner documentation.
SHELL=ROOT.parent/'LINK-COMMANDER/enclosure/A-snap-fit-abs'
paths=[*sorted((SHELL/'print').glob('*.stl')),*sorted((SHELL/'print').glob('*.step')),*sorted((SHELL/'print').glob('*.3mf'))]
paths += [SHELL/'cad'/name for name in ['COMMON_E_F_SHELL.step','base_assembled.step','lid_assembled.step']]
with zipfile.ZipFile(OUT/'3d-print/LINK_COMMANDER_ENCLOSURE_A1.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in paths:z.write(p,'LINK_COMMANDER_ENCLOSURE_A/'+str(p.relative_to(SHELL)))
 z.write(OUT/'docs/link-commander-enclosure-guide.pdf','LINK_COMMANDER_ENCLOSURE_A/PRINT_AND_ASSEMBLE.pdf')
shutil.copy2(OUT/'3d-print/LINK_COMMANDER_ENCLOSURE_A1.zip',OUT/'3d-print/LINK_COMMANDER_ENCLOSURE_A.zip') # Keep existing customer bookmarks working.
files=[*sorted((OUT/'docs').glob('*.pdf')),*sorted((OUT/'software').glob('*')),*sorted((OUT/'3d-print').glob('*'))]
(OUT/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(OUT))+'\n' for p in files))
print('Packaged',len(files),'customer downloads with SHA-256 manifest')
