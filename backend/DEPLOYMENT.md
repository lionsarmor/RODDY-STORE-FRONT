# Deployment record — 2026-10-12

- Frontend: GitHub Pages at https://roddy.world, built from this repository's main branch.
- Backend: `roddy-store.service` on the existing 143.244.168.180 droplet,
  listening only on 127.0.0.1:8091 behind Caddy.
- HTTPS API: https://store-api.143-244-168-180.sslip.io
- Caddy: existing sites preserved; store site added after successful configuration validation.
  Previous configuration backed up at `/etc/caddy/Caddyfile.roddy-store-before-20261012`.
- Payment provider: Square, US seller, USD. Public checkout remains disabled pending
  credentials, sandbox end-to-end validation, live account readiness, and tax setup.
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
payment responses, not a real Square charge.

On the droplet, Caddy validation passed and the store, Caddy, and existing Desk
Commander services remained active. HTTPS certificate issuance succeeded and
HTTPS health returned the disabled/unconfigured state before account setup.

Outstanding launch work: connect Square using the protected console helper,
verify a sandbox purchase/refund and test ZIP delivery, approve the Desk Commander
release candidate, configure applicable tax treatment and live credentials, then
enable public checkout and verify a real purchase with the owner. Receipt email
and refunds use Square; automatic download-recovery emails are not implemented.

See [README.md](README.md) for setup, operational limits, and rollback.
