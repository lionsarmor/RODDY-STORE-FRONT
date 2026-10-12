# Deployment record — 2026-10-12

- Frontend: GitHub Pages at https://roddy.world, built from this repository's main branch.
- Backend: `roddy-store.service` on the existing 143.244.168.180 droplet,
  listening only on 127.0.0.1:8091 behind Caddy.
- HTTPS API: https://store-api.143-244-168-180.sslip.io
- Caddy: existing sites preserved; store site added after successful configuration validation.
  Previous configuration backed up at `/etc/caddy/Caddyfile.roddy-store-before-20261012`.
- Payment provider: Square, US seller, USD. Sandbox credentials and location have
  been verified. Public checkout remains disabled pending production credentials,
  release approval, live account readiness, and applicable tax setup.
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

Results: 9 frontend tests and 19 backend tests passed; all three Vite entry points
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
HTTPS health now reports configured, account ready, and sandbox mode. The backend
is enabled for sandbox testing; public storefront checkout remains disabled.

Outstanding launch work: replace the sandbox token shared during setup using the
protected console helper, approve the Desk Commander release candidate, configure
applicable tax treatment and live credentials using the helper's `--mode live`, then
enable public checkout and verify a real purchase with the owner. Receipt email
and refunds use Square; automatic download-recovery emails are not implemented.

See [README.md](README.md) for setup, operational limits, and rollback.
