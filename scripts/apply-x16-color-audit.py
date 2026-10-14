"""Apply an owner-approved X16 swatch audit to display and private order artwork.

Pass --audit FILE --recipe PRIVATE_FILE --output PRIVATE_OUTPUT --revision REV.
The audit stays untouched; this command does not mark GUI review boxes complete.
Private order files must remain outside the repository's tracked files.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value, *, compact=False):
    path.write_text(json.dumps(value, ensure_ascii=False,
                               **({'separators': (',', ':')} if compact else {'indent': 2})) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('audit', 'recipe', 'output', 'revision'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    audit_path, recipe_path, output = map(Path, (args.audit, args.recipe, args.output))
    # Never place a manufacturing recipe in a tracked or customer asset directory.
    output.resolve().relative_to((ROOT / '.tools').resolve())
    preview_path = ROOT / 'src/keycap-previews/x16-v06-cherry-tkl.json'
    audit = json.loads(audit_path.read_text())
    assert audit['format'] == 'roddy-v6-color-audit' and audit['version'] == 1
    assert digest(recipe_path) == audit['sources']['manufacturingRecipeSha256'], 'Private artwork changed since audit'
    assert digest(preview_path) == audit['sources']['displayTemplateSha256'], 'Display artwork changed since audit'
    palette_file = json.loads((ROOT / 'backend/keycap_palette.json').read_text())
    assert palette_file['version'] == audit['sources']['paletteVersion']
    palette = {c['id']: c for c in palette_file['colors']}
    recipe = json.loads(recipe_path.read_text())
    preview = json.loads(preview_path.read_text())
    keys = {k['id']: k for k in preview['keys']}
    swatches, changed = [], []
    for binding in audit['bindings']:
        selected = audit['choices'][binding['id']]['paletteId']
        assert selected == binding['paletteId'] and selected in palette
        assert palette[selected]['hex'] == binding['selectedHex']
        if binding['role'] != 'swatch':
            assert selected == binding['baselinePaletteId'], 'This command only applies number-row swatches'
            continue
        assert binding['keyId'] in '12345678' and binding['position'] in ('left', 'right')
        native_id = binding['manufacturingKey']
        assert recipe['meta'][native_id]['keyId'] == binding['keyId']
        assert binding['layerIndices'] == [1 if binding['position'] == 'left' else 2]
        index = binding['layerIndices'][0]
        shape = keys[binding['keyId']]['shapes'][index]
        layer = recipe['base']['keys'][native_id]['layers'][index]
        assert layer['vectDef'] == shape['path']
        assert shape['paletteId'] == layer['colorId'] == binding['baselinePaletteId']
        shape.update(paletteId=selected, fill=palette[selected]['hex'])
        layer['colorId'] = selected
        swatches.append({'keyId': binding['keyId'], 'position': binding['position'],
                         'label': binding['label'], 'referenceHex': binding['referenceHex'],
                         'paletteId': selected, 'hex': palette[selected]['hex']})
        if selected != binding['baselinePaletteId']:
            changed.append(f"{binding['keyId']} {binding['position']}: {binding['baselinePaletteId']} → {selected}")
    assert len(swatches) == 16 and len({(s['keyId'], s['position']) for s in swatches}) == 16
    catalog_path = ROOT / 'public/data/products.json'
    catalog = json.loads(catalog_path.read_text())
    profile = next(p for p in catalog['keycapProfiles'] if p['id'] == 'x16-compatible')
    assert profile['revision'] == preview['revision'] == recipe['catalogRevision'] == recipe['revision']
    assert args.revision != profile['revision'], 'New artwork needs a new checkout revision'
    profile['revision'] = preview['revision'] = recipe['revision'] = recipe['catalogRevision'] = args.revision
    manifest = {'revision': args.revision, 'auditRevision': audit['revision'],
                'auditSha256': digest(audit_path), 'swatches': swatches}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.touch(mode=0o600, exist_ok=True)
    output.chmod(0o600)
    write_json(output, recipe, compact=True)
    write_json(preview_path, preview, compact=True)
    write_json(catalog_path, catalog)
    write_json(ROOT / 'src/keycap-artwork/x16-number-row-colors.json', manifest)
    print('\n'.join(changed))
    print(f'Applied {len(changed)} changes from audit {audit["revision"]}; all 16 swatches recorded.')


if __name__ == '__main__':
    main()
