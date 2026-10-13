# Manual newsletters from the RODDY admin

Admin → **Newsletters & ads** collects explicit opt-ins and creates newsletters
with text, pictures, product offers, prices, buttons and color palettes. Everything
runs in the existing Vue admin and droplet FastAPI service. **There is no Resend,
SMTP server, automatic email sending, or additional delivery account.** The owner
sends using their existing Proton Mail or Gmail account.

The same instructions appear beside the admin controls:

1. Process every unsubscribe reply first. Suppress that address in admin. Future
   exports exclude it, and submitting the signup form again cannot reactivate it.
2. Add a valid public postal address or registered PO box to the footer. You can
   collect signups, save drafts and preview without one; sending exports require it.
3. Save the edition and prepare a fresh export immediately before sending. Put
   **your own address in To**, and **one recipient batch in BCC**. Never use To or
   CC for customer addresses. Each batch has at most 50 subscribers; this is not
   a promise about your account's per-message or daily limits.
4. Copy the subject and formatted email body separately. Send a test to yourself
   before mailing subscribers. Inspect images, links, offer prices and the footer.
   If rich clipboard copy is unavailable, open the HTML download, select/copy its
   rendered content, and paste into the composer. Plain-text copy is also available.
5. Send each batch once and record the edition only when all batches are complete.
   This record is **self-reported**, not proof of sending, receipt or delivery.

The site cannot read the owner's inbox, process unsubscribe replies automatically,
or detect whether a batch has already been sent. Keep track of batches in the
mailbox. Old downloaded lists cannot be revoked; discard them and refresh before
each mailing. Reply-based unsubscribe and an email link are included in both HTML
and plain text. There is no fabricated one-click unsubscribe header on manual mail.

Public signup at `/#/newsletter` and the small corner invitation uses explicit
single opt-in, stored consent copy/time, a honeypot, same-origin checks and IP
throttling. It sends no confirmation email and does not verify ownership of the
submitted mailbox. Purchases and forum accounts never automatically join the list.
Public responses do not disclose whether an address already exists. The invitation
waits 25 seconds, initially shows a compact invitation (the email form opens only
when the visitor chooses to sign up), does not take focus, hides on cart/contact/newsletter pages and
active dialogs, and respects X dismissal for 30 days when storage is available.

## Data and access

`newsletter_subscribers`, `newsletter_settings` and `newsletter_campaigns` are
additive tables in `STORE_DATABASE`. They use the existing mode-600 SQLite DB and
GitHub-owner authorization. Subscriber data and draft copy never enter the public
catalog or repository. Keep regular SQLite backups with the existing order backup
process. CSV downloads contain **all statuses**, including suppressed addresses;
they are private backups, not ready-to-send recipient lists. CSV formula-leading
values are escaped. Recipient batches contain active opt-ins only.

New images are compressed and uploaded to `public/img/newsletters/` using the
existing GitHub image uploader. Those image files are public and may trigger a
Pages build. Copy remains private. Drafts save independently of catalog Publish.
Concurrent draft changes return a conflict rather than overwriting another edit;
the owner can reload or save their edits as a new edition. Sent editions are read
only and can be duplicated. Admin navigation preserves unsaved editor state until
the page is closed; closing warns about unsaved edits.

Newsletter JSON is limited to 64 KiB by Caddy and the application. Other POST
endpoints retain their 8 KiB application limit. Content has at most 12 sections,
bounded text, HTTPS-only images/links and escaped HTML; there is no arbitrary HTML
editor or server-side remote image fetching. Preview is in a sandboxed iframe.

## Deployment and validation

Deploy `app.py`, `newsletter.py` and `newsletter_mail.py` alongside the existing
backend files. Change only the store API site's Caddy body limit to `64KB`, validate
Caddy, and restart only `roddy-store`. Existing checkout, forum, fulfillment and
paid files stay in place. Migration occurs at application start. No API secrets or
mailer configuration are needed.

```sh
.tools/checkout-venv/bin/python3.12 -m unittest discover -s backend -p 'test_*.py'
npm test
npm run build
git diff --check
```

Newsletter tests use a temporary DB and fake GitHub owner/provider. They exercise
private access, consent/validation, persistence, suppression, CSV escaping, draft
conflicts, safe rendering, batch boundaries, stale audience checks, manual records
and body limits without sending email. Browser checks use an isolated local API;
do not create test subscribers or newsletters in the production database.

Provider and footer guidance is linked in admin: [Proton recipients](https://proton.me/support/contact-groups),
[Gmail sending limits](https://support.google.com/mail/answer/22839), and
[FTC commercial email guidance](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business).
