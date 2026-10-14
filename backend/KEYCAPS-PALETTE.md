# Keycap palettes and individual colors

`keycap_palette.json` is the shared selection fetched read-only from the official Yuzu Playground on 2026-10-14: 321 colors with their Yuzu IDs, display HEX values and CMYK references. Customer and admin controls select these IDs. Raw HEX input is rejected by the order API, even if the HEX happens to match a palette entry.

`keycap_color_map.json` records CIE76 matches with reviewed overrides for the earlier artwork and preset colors. It is used to migrate catalog defaults; it does not allow arbitrary customer color values. The v6 defaults are GR002 (White), GR009 (5467U) and BL003 (7451U). Screen colors remain approximations of the physical print.

A selection includes group IDs (`alpha`, `modifiers`, `accents`) and `keyColors`, a map from a layout's stable display key IDs to palette IDs. An empty map uses group colors. Overrides persist when groups change and can be reset independently. Cart identity sorts overrides, so insertion order cannot split identical designs. A color change invalidates an existing checkout quote.

The private recipe's `meta` maps each display `keyId` to the existing supplier key ID and identifies text layers that adjust between GR001 and GR002 for contrast. Every fixed legend, number-row swatch, symbol and arrow layer also uses palette IDs. A recursive output check rejects any remaining unapproved colorId. Paid snapshots freeze the completed manufacturing JSON, the selection and the palette references; downloading historical packets never re-renders them with new defaults.

To add a different physical layout, supply its private recipe with the same paletteVersion, unique display keyIds and autoLegendLayers, then add its matching display-only preview. Profiles sharing a layout can have separate products and defaults. Unknown override keys are rejected against the chosen layout.

The number-row olive swatch (2, right) uses GN037 / 575U (#6F7A61), and dark blue (7, left) uses BL026 / 2747U (#2E4783), replacing the brown and lighter-blue automatic matches. Arrows offer small and bold geometry with either GR001 black or GR002 white ink. The same geometry and ink selection is used in the storefront and private order snapshots.

All manufacturing recipes stay on the droplet. Customers receive display geometry and their selection; only authenticated owner order downloads contain Yuzu manufacturing files. The quote and checkout body limit is 256 KiB to accommodate multi-design carts with individual colors.

Validation for this change includes paid-order packet tests, all 321 colors across 29 complete layout cases compared against the frontend, and an exact JSON import/export round trip through the current Yuzu editor. Yuzu's own print-eligibility function returned no problems. The read-only editor check blocked all non-GET/HEAD network requests and did not save an account design or submit an order.
