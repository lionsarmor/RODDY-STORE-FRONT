# Deployment record — 2026-10-12

- Frontend: GitHub Pages at https://roddy.world, built from this repository's main branch.
- Backend: `roddy-store.service` on the existing 143.244.168.180 droplet,
  listening only on 127.0.0.1:8091 behind Caddy.
- HTTPS API: https://store-api.143-244-168-180.sslip.io
- Caddy: existing sites preserved; store site added after successful configuration validation.
  Previous configuration backed up at `/etc/caddy/Caddyfile.roddy-store-before-20261012`.
- Payment provider: Square, US seller, USD. The owner configured production
  credentials using the protected console helper. Live account readiness and
  production checkout creation have been verified; public checkout is enabled.
- Square's hosted checkout currently displays the seller name `intoto film`.
- Desk Commander: $3.99, project GitHub button enabled. Weather Commander and Shadow
  Over Space remain free with unchanged release links.
- Private release candidate: UI review build from DESK-COMMANDER commit
  `9c5f9a1b3aeff26a04e947867790aa22a2f90dff` (draft PR #1 remains for owner review).
  ZIP SHA-256: `4938ba94ecbf8e29a13dcccce285fa44ccfcb5268076b35a51cd38815534d833`.
  Stored outside Pages under `/var/lib/roddy-store/files/`. Sandbox uses a separate
  generated test ZIP and cannot unlock this release candidate.

Validation completed before publication:

```sh
npm test
npm run build
python3 -m unittest discover -s backend -p 'test_*.py'
```

Results: 9 frontend tests and 20 backend tests passed; all three Vite entry points
built. Playwright browser checks covered $3.99 product UI, one-copy digital cart,
free release/GitHub links, unpaid versus paid order UI, destination validation,
retry idempotency, and a mocked Square redirect. These browser checks used mocked
payment responses. A separate end-to-end test subsequently used real Square
sandbox API responses and Square's hosted sandbox payment panel:

- The live storefront opened a $3.99 sandbox checkout; checkout was enabled only
  in the test browser's catalog response, leaving the public catalog disabled.
- A simulated payment unlocked the receipt page's test ZIP download. Its SHA-256
  matched the private sandbox manifest; it contained only `SANDBOX-READ-ME.txt`.
- A sandbox refund request returned `PENDING`. Subsequent download access was
  immediately denied with HTTP 403, and the receipt returned `paid: false` with
  no download links. No real money was charged or refunded.

On the droplet, Caddy validation passed and the store, Caddy, and existing Desk
Commander services remained active. HTTPS certificate issuance succeeded and
HTTPS health now reports configured, account ready, live mode, and checkout
enabled. A browser test opened Square's production checkout showing DESK COMMANDER
at $3.99 with no JavaScript errors. No real payment was submitted. The private
release ZIP's SHA-256 was rechecked against its manifest before enabling checkout.

Remaining owner checks: complete a real purchase to validate live settlement and
delivery, review the Desk Commander draft PR/release candidate, and confirm
applicable tax treatment. Automatic tax calculation is not implemented; checkout
charges exactly $3.99. Replace the sandbox token shared during setup before any
future sandbox use. Receipt email and refunds use Square; automatic
download-recovery emails are not implemented. Existing free/source releases may
remain publicly accessible; the purchase delivers the packaged private build.

See [README.md](README.md) for setup, operational limits, and rollback.
