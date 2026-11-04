"""Prepare storefront downloads from owner-supplied release files, not private source trees."""
from pathlib import Path
import zipfile,shutil,hashlib,json
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.tools/customer-docs/source'
OUT=ROOT/'public/downloads'
# Version and native-only validation live in the dedicated Weather packager.
import subprocess,sys
subprocess.run([sys.executable,str(ROOT/'tools/package-weather.py'),str(SOURCE/'WEATHERCMD.zip')],check=True)
shutil.copy2(SOURCE/'Shadow_Over_space.bin',OUT/'software/Shadow_Over_space-v0.1.0.bin')
# Preserve the reviewed Rev H/I public case bundle. Do not regenerate the retired
# E/F shell from the owner's source tree or publish electrical/manufacturing files.
bundle=OUT/'3d-print/LINK_COMMANDER_FDM_CASES.zip'
with zipfile.ZipFile(bundle) as z:
 assert z.testzip() is None, 'Corrupt Link Commander case download'
 for variant in ['dongle-direct-concept','dongle-cable','through-hole-dual-cable']:
  for part in ['base','lid']:
   assert f'enclosures/{variant}/{part}-PRINT.stl' in z.namelist()
for alias in ['LINK_COMMANDER_ENCLOSURE_A1.zip','LINK_COMMANDER_ENCLOSURE_A.zip']:
 shutil.copy2(bundle,OUT/'3d-print'/alias) # Keep existing customer bookmarks working.
files=[*sorted((OUT/'docs').glob('*.pdf')),*sorted((OUT/'software').glob('*')),*sorted((OUT/'3d-print').glob('*'))]
(OUT/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(OUT))+'\n' for p in files))
print('Packaged',len(files),'customer downloads with SHA-256 manifest')
