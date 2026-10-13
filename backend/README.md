# Droplet checkout, community, newsletters and paid downloads

Manual newsletters and private subscriber records use the same database and service.
See [NEWSLETTERS.md](NEWSLETTERS.md) for the admin workflow and backup requirements.

The same service also hosts the contact page's General forum, handle accounts and
GitHub-owner moderation. See [FORUM.md](FORUM.md) for public/private contact flow,
session handling, administration and validation.

The GitHub Pages storefront uses this separate FastAPI service on the existing
DigitalOcean droplet. Square hosts payment entry; the droplet never receives card
numbers. There is no Payhip account, Stripe server, Cloudflare Worker, or additional
shop subscription in this implementation. Square processing fees still apply.

Square is selected for this store's **US seller account and USD prices**. Its
[online payment API pricing](https://developer.squareup.com/us/en/online-payment-apis)
currently lists 2.9% + $0.30 per transaction (about $0.42 on $3.99 before any
applicable extra fees). Confirm the account's actual rate before launch.

## Local validation

Use Python 3.12 or later and a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python -m unittest discover -s backend -p 'test_*.py' -v
npm test
npm run build
```

Tests inject a fake payment provider. There is **no HTTP test-payment bypass** in
the deployed service. A sandbox purchase through Square remains required.

## First deployment

1. Verify the SSH host fingerprint against the droplet console. Use the dedicated
   deployment key. Inspect running services and the current Caddyfile first.
2. Upload this repository's `backend/` directory to a temporary deployment
   directory on the droplet. Ensure `python3-venv` is installed; do not upgrade or
   restart unrelated system services as part of this deployment.
3. From that directory run `sh backend/deploy/install.sh` as root. The service
   runs as `roddystore`, bound to **127.0.0.1:8091**. Existing Desk Commander and
   Agent Commander services keep their own ports and data.
4. Install the approved release ZIP into `/var/lib/roddy-store/files/`, owned by
   `root:roddystore`, mode `640`. Update `/etc/roddy-store/digital-products.json`
   with its filename and SHA-256. Do not put paid files under `public/`, commit
   them to this public repo, or serve this directory with Caddy. Keep old files
   after release updates: existing orders retain the purchased filename/hash.
5. Add `deploy/Caddyfile.snippet` as a **new site** in the existing Caddyfile.
   Validate with `caddy validate --config /etc/caddy/Caddyfile` before
   `systemctl reload caddy`. Keep a backup for rollback. Do not enable access
   logging for this API: download paths contain short-lived bearer tickets.
   The request-body limit and HTTPS reverse proxy are required.
6. Check `systemctl status roddy-store` and
   `curl https://store-api.143-244-168-180.sslip.io/health`. With no credentials,
   the expected response says `configured: false`, `checkoutEnabled: false`.
   Prefer `api.roddy.world` once its DNS points to the droplet; update
   `STORE_PUBLIC_URL` and the storefront endpoint together.

## Connect Square securely

Create a US seller account and payout bank connection at
[Square](https://squareup.com/signup), then a developer application at
[Square Developer](https://developer.squareup.com/apps).

Use **sandbox** credentials first. In the droplet console run:

```sh
python3 /opt/roddy-store/backend/deploy/configure-square.py
```

The helper prompts for the token without echoing it, verifies it with Square,
automatically selects an eligible USD location (or asks you to choose if there
are several), saves the connection in `/etc/roddy-store/store.env`, and restarts
only this service. The file stays mode `640`, owner `root:roddystore`. It uses a separate sandbox database
and generates a test ZIP containing no paid software. Sandbox checkout refuses
files that are not explicitly marked as test assets. Never paste secrets into
chat, the public catalog, GitHub, browser code, or shell command arguments.
The backend needs Orders read/write and Payments read/write access to its own
seller account; location health checks also need location access.

Set `SQUARE_MODE=sandbox`, `STORE_CHECKOUT_ENABLED=true`, then restart only
`roddy-store`. `/health` verifies the location is active, denominated in USD, and
capable of card processing. This checks account readiness, not a completed sale.

Keep the **published** frontend `checkoutEnabled` false during sandbox testing.
Use a local unpublished catalog with the endpoint and checkout enabled, and add
that local origin to `ALLOWED_ORIGINS`. Browser draft previews intentionally block
checkout. Test a sandbox purchase, canceled payment, retry, order return,
test ZIP bytes/hash, expired link refresh, and refunded download rejection.
Verify the real release ZIP hash privately over SSH.
Use Square's official [sandbox testing documentation](https://developer.squareup.com/docs/devtools/sandbox/payments).

Before live launch, run the same helper with `--mode live` and enter live
credentials/location. This selects the real private release manifest and a
separate live database. Check the connection and arrange applicable tax treatment. The service
charges the catalog's exact USD price: tax calculation and promotions are not
implemented. Then publish the HTTPS endpoint and enable customer checkout in
**Admin → Checkout & Square**. Verify a real purchase and refund with the owner.
Wallet availability depends on the Square account, browser, and buyer location.

## Payment and delivery behavior

- Active, available paid digital products require a private release manifest;
  one copy per product is allowed. Free downloads remain direct public links.
  With physical checkout enabled, Printify and office items share the same cart;
  see [COMMERCE.md](COMMERCE.md) for shipping, inventory and fulfillment.
- The server re-prices IDs from the published GitHub catalog. Browser-supplied
  prices are ignored. Each persisted attempt snapshots the trusted price/file.
- Persistent request references and Square idempotency keys recover network
  retries. A different cart cannot reuse an attempt. Attempts expire after one
  hour; already-created Square links may remain payable, so do not deliberately
  reuse or share them. Reopening the same attempt does not charge automatically.
- The return URL uses a random 256-bit order reference in a fragment, outside
  HTTP logs/referrers. Treat the whole bookmarked order page as a private receipt.
  It can refresh downloads for 30 days. Support can use the Square receipt after
  expiry; automatic email delivery/recovery is not implemented.
- The server retrieves the Square order and payment on every order check and
  download. Correct order, seller location, USD total, completed payment, and no
  refunds are required. Redirects and client flags never authorize a download.
  There is no payment webhook to spoof or maintain in this small implementation.
- Tickets expire after 15 minutes. Files are checked against their stored hash.
  A refund blocks future downloads; bytes already downloaded cannot be revoked.
- SQLite stores orders, file snapshots, download-ticket hashes, and rate limits.
  Back up `/var/lib/roddy-store` plus the protected configuration. Keep those
  backups private. Do not mix live and sandbox databases; archive sandbox data
  and set a fresh `STORE_DATABASE` path before switching to live mode.
- The admin order list uses the existing GitHub owner sign-in and returns only
  the latest 100 attempts, without receipt tokens or private file paths. It
  shows the last verified status; Square is authoritative for current payments,
  refunds, and disputes. Promotions, automated dispute handling and tax reporting
  are not implemented. Mixed fulfillment is described in COMMERCE.md.

## Operations and rollback

```sh
systemctl status roddy-store --no-pager
journalctl -u roddy-store -n 100 --no-pager
curl http://127.0.0.1:8091/health
```

To stop sales, disable checkout in the public catalog and set
`STORE_CHECKOUT_ENABLED=false`, then restart the store service. Existing paid
order verification/downloads continue. To remove the API entirely, stop/disable
`roddy-store`, remove only its Caddy site, validate/reload Caddy, and retain private
order backups. Do not stop the other droplet services.

Removing the formerly free storefront ZIP prevents future Pages downloads.
Earlier public GitHub releases, Git history, and customer copies remain public;
the store price covers the packaged download, not exclusive access to source.

API references: [create payment link](https://developer.squareup.com/reference/square/checkout-api/create-payment-link),
[retrieve order](https://developer.squareup.com/reference/square/orders-api/retrieve-order),
[get payment](https://developer.squareup.com/reference/square/payments-api/get-payment).

For mixed carts, Printify fulfillment, office shipping and inventory, see [COMMERCE.md](COMMERCE.md).
