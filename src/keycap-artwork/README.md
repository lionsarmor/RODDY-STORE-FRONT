# RODDY retro X artwork

Five original X symbols inspired by the requested Macintosh, Tandy, IBM and
Packard Bell styles. The smooth and pixel rainbow variants follow the user's
two supplied visual references. These are X designs, not brand logo replicas.

`retro-x/COMPARE_RETRO_X.svg` compares all five on off-white and v6 blue.
The same folder contains standalone 64 × 64 SVG marks. Every colored shape is
an outlined path: no embedded bitmap, external font, clipping mask or live stroke.

`retro-x-marks.json` stores source-coordinate artwork for future layouts.
Regenerate it and the SVGs with `python3 scripts/build-retro-x-artwork.py`.
The public storefront uses normalized preview shapes only. Supplier-specific
manufacturing layers are installed privately on the droplet; they are not
committed or exposed through customer downloads.

`number-row-labels.json` contains outlined original v6 color-name labels and the preserved top number/shifted-symbol paths, without lower box frames. Rebuild with `scripts/build-number-row-labels.py` (fontTools and Liberation Mono Bold). Each label has three fixed-width characters, a 1.15 mm cap height, the same baseline and the same advance, without wrapping or per-word compression. The display preview and private template use the same paths.
