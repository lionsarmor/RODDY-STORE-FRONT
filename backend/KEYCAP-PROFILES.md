# Custom keycap sets and the manual fulfillment queue

The X16 product has a live v6 designer. A catalog `keycapProfiles` record defines
its validated physical template, revision, defaults and allowed symbols/arrows.
A product links it with `keycaps: {profileId: "x16-compatible"}`. The normal
`/product/<product-id>` route gives every set its own page. Several products can
share a profile, and profiles can share a physical template.

## Owner workflow

1. In **Admin → Keycap profiles**, duplicate or add a profile. Choose its template,
   name, description, starting colors and available symbols/arrows.
2. Select **Create product page for this profile**. New pages start hidden and
   coming soon. Edit their name, images and description. Use the Keyboard profile
   tab to change the assigned profile and enter confirmed US/Canada shipping.
3. After confirming manufacturing, sample, retail price and shipping, clear
   Pricing pending, choose Available, enable visibility and publish the catalog.
   Set `trackStock: false`; the server treats these as custom manual fulfillment,
   independent of office inventory and Printify.
4. Open **Orders → New keycap orders**. Download an individual ZIP or a batch of
   up to the oldest 100 pending orders. Import only each `*-yuzu.json` into Yuzu.
   `ORDER_DETAILS.json` contains the quantities, delivery details, customer email
   and phone, Square reference, amounts, selections, layout fit and checksums.
5. Place the supplier order yourself. Check **Submitted to maker** and optionally
   record its reference. Unchecking returns an unshipped order to the queue.
   Downloading does not check off an order or purchase anything. Add tracking
   when it ships; the customer's private order page shows the update.

Payment is verified by Square before a job enters the queue. The complete JSON,
profile definition and template checksum are frozen in the quote/order, so
later catalog or template edits cannot change a customer's paid design. Different
designs of the same product remain separate cart lines. Shipping groups those
lines by product for its first/additional item rates.

## Files and notifications

The worker atomically writes complete private order folders under
`/var/lib/roddy-store/keycap-orders/RODDY-<order-uuid>/` (or `KEYCAP_PACKETS_DIR`).
Folders are mode 700, files mode 600, and nothing is served by a public static URL.
The admin ZIP endpoint can reconstruct a packet from SQLite even if disk writing
fails. The worker retries disk errors. Repeated payment checks do not duplicate
jobs or rewrite an existing completed folder. Historical packets remain for your
records after refunds; the admin queue excludes payments no longer confirmed.
Recheck the payment before submitting any downloaded/synced order to a maker.

No mail account, SMTP server or third-party notification account is needed.
**Enable sale notifications on this device** in admin asks the browser for
permission. A private poll checks for new confirmed sales about every 30 seconds
while admin is open and connected. Alerts cover all products, not just keycaps;
notification content includes product names and total, without customer addresses.
Browser/OS notification settings and background throttling still apply. Closing
admin stops browser alerts; orders and payment events remain saved on the droplet.

Optional SSH transfer using the owner's existing `roddy-store` host alias:

```sh
mkdir -p "$HOME/Desktop/RODDY-Keycap-Orders"
chmod 700 "$HOME/Desktop/RODDY-Keycap-Orders"
rsync -a --chmod=D700,F600 --exclude='.preparing-*' \
  roddy-store:/var/lib/roddy-store/keycap-orders/ \
  "$HOME/Desktop/RODDY-Keycap-Orders/"
```

This copies historical packets, including ones already submitted or refunded;
admin remains the source of truth for current payment and fulfillment status.
No deletions or automatic maker submissions are performed.

## Adding a different physical keyboard layout

Only the validated ANSI 87-key Cherry template ships initially. A profile name
cannot change key sizes, stems or row sculpt. To support a genuinely different
keyboard, install its reviewed manufacturing recipe privately at
`/var/lib/roddy-store/keycap-templates/<template-id>.json` (or
`KEYCAP_TEMPLATES_DIR`), owned by `roddystore`, with directory mode 700 and file
mode 600. Do not commit manufacturing recipes to this public repository. Register
separate display geometry in `src/keycap-previews/` and `KEYCAP_PREVIEWS` in
`src/keycaps.js`. Display assets contain colors and drawing paths, without Yuzu
layout/template mappings or an export function. The private recipe contains:

- `base`: an actual Yuzu export with layout, sizes, rows, homing keys, templates
  and embedded printable vector layers; never remote font/vector dependencies.
- `meta`: every layout key mapped to source key, `alpha`/`modifiers`/`accents` color
  group and the actual supplier printable mask.
- `marks`: each supported Commander replacement, already transformed into the
  correct key canvas coordinates; the preview uses separate display shapes.
- `arrows`: bold white replacements indexed by the four arrow key IDs.
- `id`, `revision`, `name`, `compatibility` and source checksum.

Validate every new layout and option against the supplier print masks and import
it into the maker editor before offering it. The color recoloring policy preserves
the v6 swatches: `#F7F7F5` and `#0A0D12` legend layers automatically switch light or
dark; colored swatches stay fixed. If a new recipe uses these values for fixed art,
extend the layer semantic metadata/generator rather than recoloring that art.

The initial source is `x16-keycaps/brand/v06/yuzu/RODDY_X16_v06_Yuzu.json`,
previously round-tripped through Yuzu. The original private recipe and its v6 colors/vector layers remain unchanged.
Frontend checks verify preview choices; backend CI uses synthetic geometry so
production manufacturing files never enter public test artifacts. The recipe includes exact Commander-key v6
artwork, the published OtterX PCB X, original RODDY flight X and borderless R+dot.
OtterX source: Joseph Burks / RetroRemake, revision
`6a03c72046c8cc3bded9b9b60a628c666e390733`,
`parts/footprints.pretty/Fancy_X_FCu.kicad_mod`:
https://github.com/RetroRemake/OtterX/blob/6a03c72046c8cc3bded9b9b60a628c666e390733/parts/footprints.pretty/Fancy_X_FCu.kicad_mod
The upstream CERN-OHL-W-2.0 license is in `keycap_templates/OTTERX_LICENSE.txt`.

## Private API

All admin endpoints require the existing verified GitHub-owner bearer token.

- `GET /admin/orders?view=keycaps`: oldest 100 paid orders awaiting submission.
- `POST /admin/orders/<uuid>/keycaps`: `{action:"download"}` returns a private ZIP;
  `{action:"submitted",supplierReference:"optional"}` checks off a set;
  `{action:"pending"}` reverses check-off for an unshipped set.
- `POST /admin/keycaps/packets`: ZIP of up to 100 pending order folders.
- `POST /admin/orders/<uuid>/shipment`: existing tracking API, `kind:"keycaps"`.
- `GET /admin/sales`: establish current event cursor and pending keycap count.
- `GET /admin/sales?after=<cursor>`: up to 20 verified sale events plus next cursor.

Run `npm test`, `npm run test:backend` and `npm run build`. Never run tests against
the production database. Product checkout remains gated by its availability,
final price, physical-checkout configuration and destination shipping rate.

Customer JSON export is disabled. Manufacturing packet downloads require owner
authentication and a paid keycap order. The public preview necessarily displays
the artwork, and older published assets/repository revisions cannot be recalled.
