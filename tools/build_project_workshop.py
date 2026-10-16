#!/usr/bin/env python3
"""Export linked project documents to PRIVATE backend storage, never public/.

python3 tools/build_project_workshop.py --workspace ../ --output /tmp/roddy-workshop
Upload output to /var/lib/roddy-store/project-workshop/library after validation.
No source designs are changed. Re-run after updating the project repositories.
"""
import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

EXTENSIONS = {'.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.pdf',
              '.md', '.txt', '.csv', '.json', '.zip', '.stl', '.step', '.stp', '.3mf',
              '.wrl', '.obj', '.mtl', '.glb', '.gltf', '.bin', '.drl', '.gbr', '.pos',
              '.kicad_pro', '.kicad_pcb', '.kicad_sch', '.kicad_sym', '.kicad_mod',
              '.xml', '.dxf', '.scad', '.fcstd', '.woff', '.woff2', '.eml'}
SPECIAL = {'sym-lib-table', 'fp-lib-table'}
RELOCATIONS = {
    'KeychainKreatures/revisions/C7_P5-handheld/concepts/early_concepts/branding/roddy-logo.svg':
        'KeychainKreatures/revisions/C7_P5-handheld/branding/roddy-logo.svg',
    'KeychainKreatures/revisions/C7_P5-handheld/concepts/early_concepts/enclosure/B-keyring-bezel/OPEN_ME.html':
        'KeychainKreatures/revisions/C7_P5-handheld/enclosure/B-keyring-bezel/OPEN_ME.html',
}


class Links(HTMLParser):
    def __init__(self, source):
        super().__init__(); self.links = []; self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.links.extend(v for k, v in attrs if k in ('href', 'src', 'poster') and v)


def build(workspace, output):
    workspace, output = workspace.resolve(), output.resolve()
    roots = {name: workspace / name for name in ('KeychainKreatures', 'LINK-COMMANDER')}
    if any(output.is_relative_to(p) for p in roots.values()):
        raise ValueError('Export outside the project source directories.')
    if output.exists():
        raise ValueError('Use an empty output path; exports never overwrite an existing library.')
    entries = []
    kk = 'KeychainKreatures/revisions/C7_P5-handheld/'
    lc = 'LINK-COMMANDER/revisions/E-ps2-through-hole/'

    def add(project, group, title, description, path, archive=False):
        entries.append(dict(id=f'document-{len(entries)+1}', project=project, group=group,
                            title=title, description=description, path=path, archive=archive))

    add('shared', 'Buying & batch planning', 'Start here · batch purchasing', 'Compare 1-, 10- and 50-device batches, estimated costs and supplier routes.', 'KeychainKreatures/purchasing/OPEN_ME.html')
    for project, base in [('kk', kk+'purchasing/batches/'), ('lc', lc+'procurement/batches/')]:
        for count in (1, 10, 50):
            add(project, 'Buying & batch planning', f'{count} device'+('s' if count>1 else '')+' · purchasing pack', 'BOM, supplier links, PO drafts, PCBWay files and shipping estimate. Planning allowances remain identified in the pack.', base+f'{count:02d}-devices/OPEN_ME.html')
        add(project, 'Sourcing & audits', 'Mouser parts audit', 'Compatibility, sourcing evidence and outstanding component decisions.', (kk if project=='kk' else lc)+'sourcing/mouser/OPEN_AUDIT.html')
    add('kk', 'Boards & manufacturing', 'C.7 / P.5 · current hardware', 'Main and power board projects, native PCB renders, assembly notes and review files.', kk+'OPEN_ME.html')
    add('kk', 'Boards & manufacturing', 'PCBWay · exact upload guide', 'Separate main-board and populated power-board manufacturing packages.', kk+'PCBWay/OPEN_ME.html')
    add('lc', 'Boards & manufacturing', 'Revision E · through-hole hardware', 'Current Link Commander PCB, assembly drawings, BOM and PCBWay packages.', lc+'OPEN_ME.html')
    add('kk', 'Cases & 3D inspection', 'Shell B · keyring & bezel', 'Interactive inspection, green rear view, colours, STL, STEP and print files.', kk+'enclosure/B-keyring-bezel/OPEN_ME.html')
    add('lc', 'Cases & 3D inspection', 'Snap-fit ABS case', 'Interactive enclosure inspection and printable case files for revisions E and F.', 'LINK-COMMANDER/enclosure/A-snap-fit-abs/OPEN_ME.html')
    add('kk', 'Cases & 3D inspection', 'Hardware review gallery', 'CAD review renders and mechanical references.', kk+'REVIEW_GALLERY.html')
    add('kk', 'Branding & renders', 'RODDY branding', 'Current hero images and product artwork.', kk+'branding/OPEN_ME.html')
    add('kk', 'Branding & renders', 'Colourways, mystery & exploded view', 'Retro and pastel trios, individual colours and the native hardware poster.', kk+'branding/collection_01/OPEN_ME.html')
    add('lc', 'Branding & renders', 'Link Commander · mystery branding', 'Landing-page teaser and its reference artwork.', 'LINK-COMMANDER/branding/mystery-v1/OPEN_ME.html')
    # Include every other tracked/current OPEN guide, while making superseded work explicit.
    covered = {e['path'] for e in entries}
    for name, root in roots.items():
        for file in sorted(root.rglob('OPEN_ME.html')):
            rel = file.relative_to(workspace).as_posix()
            if rel in covered or any(p.startswith('.') for p in file.relative_to(root).parts):
                continue
            if name == 'LINK-COMMANDER' and '/purchasing/' in rel:
                continue  # Obsolete ignored procurement exports; current batches are above.
            project = 'kk' if name == 'KeychainKreatures' else 'lc'
            archive = any(p in rel for p in ('early_concepts', 'C6_P4', 'D-din', 'F-ps2', 'G-home', '/PO/'))
            title = file.parent.name.replace('_', ' ').replace('-', ' · ')
            add(project, 'Older revisions & concepts' if archive else 'Project indexes', title,
                'Preserved reference; not the current production choice.' if archive else 'Project navigation and related files.', rel, archive)

    queue = [workspace / e['path'] for e in entries]
    visited, files, missing, native = set(), {}, set(), set()
    output.mkdir(parents=True)
    while queue:
        source = queue.pop().resolve()
        try:
            rel = source.resolve().relative_to(workspace).as_posix()
        except ValueError:
            continue
        parts = Path(rel).parts
        if not parts or parts[0] not in roots or any(p.startswith('.') or p in ('node_modules', '__pycache__') for p in parts):
            continue
        if rel in visited:
            continue
        visited.add(rel)
        if not source.exists():
            missing.add(rel); continue
        if source.is_dir():
            queue.extend(source.iterdir()); continue
        if source.suffix.lower() not in EXTENSIONS and source.name not in SPECIAL:
            continue
        dest = output / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        if source.suffix == '.html':
            def relocate(match):
                link = urlsplit(match[3])
                if link.scheme or link.netloc or not link.path:
                    return match[0]
                candidate = (source.parent / unquote(link.path)).resolve()
                if not candidate.is_relative_to(workspace):
                    return match[0]
                replacement = RELOCATIONS.get(candidate.relative_to(workspace).as_posix())
                if not replacement:
                    return match[0]
                value = os.path.relpath(workspace / replacement, source.parent)
                if link.fragment:
                    value += '#' + link.fragment
                return match[1] + match[2] + value + match[2]
            dest.write_text(re.sub(r'''((?:href|src)\s*=\s*)(["'])(.*?)\2''', relocate, source.read_text(), flags=re.I))
        files[rel] = {'bytes': dest.stat().st_size, 'sha256': hashlib.sha256(dest.read_bytes()).hexdigest()}
        if source.suffix == '.kicad_pro':
            queue.append(source.parent); native.add(source.parent)
        if source.suffix == '.html':
            for link in Links(dest.read_text()).links:
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                queue.append(source.parent / unquote(parsed.path))
    # Downloadable project folders preserve neighbouring symbols, footprints and models.
    for folder in sorted(native):
        rel = folder.relative_to(workspace).as_posix()
        target = '_downloads/' + folder.parent.name + '__' + folder.name + '__' + hashlib.sha256(rel.encode()).hexdigest()[:8] + '.zip'
        (output / '_downloads').mkdir(exist_ok=True)
        with zipfile.ZipFile(output / target, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(files):
                if path.startswith(rel + '/'):
                    archive.write(output / path, path[len(rel)+1:])
        files[target] = {'bytes': (output/target).stat().st_size, 'sha256': hashlib.sha256((output/target).read_bytes()).hexdigest()}
        current = '/C7_P5-handheld/' in rel or '/E-ps2-through-hole/' in rel
        add('kk' if rel.startswith('KeychainKreatures/') else 'lc', 'Boards & manufacturing' if current else 'Older revisions & concepts', 'KiCad source ZIP · '+folder.parent.name+' / '+folder.name, 'Download the complete project folder before opening it in KiCad.', target, not current)
    # Validate the exported links as well as the source graph (including filtered types).
    for path in files:
        if not path.endswith('.html'):
            continue
        for link in Links((output / path).read_text()).links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(path), unquote(parsed.path)))
            if target not in files and not any(f.startswith(target.rstrip('/')+'/') for f in files):
                missing.add(target)
    manifest = {'updatedAt': datetime.now(timezone.utc).isoformat(),
                'projects': [{'id':'kk','name':'Keychain Kreatures'}, {'id':'lc','name':'Link Commander'}],
                'entries': entries, 'files': files, 'missingSourceLinks': sorted(missing)}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'entries':len(entries), 'files':len(files), 'bytes':sum(f['bytes'] for f in files.values()), 'missing':sorted(missing)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.workspace, args.output)
