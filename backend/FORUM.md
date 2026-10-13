# Contact and community board

The storefront's `/#/contact` page contains one public General board and a private
contact-email dialog. Header and footer navigation both link to it.

Visitors can read without an account, create a unique handle/password, start
topics and reply. Handles use 3–24 ASCII letters, numbers or underscores and are
case-insensitive for sign-in/uniqueness. Passwords use salted scrypt hashes;
opaque session tokens are hashed in SQLite and expire after 30 days. Passwords
are never stored in browser storage. Signing out revokes that browser session.
Registration/sign-in/write requests require the configured storefront Origin.

Posts are plain text, rendered through Vue's escaping, with titles up to 100
characters and bodies up to 1,800. New topics page in groups of 20. Threads show
their latest 50 replies in chronological order, with earlier replies available.
IP limits cover reads, account creation, sign-in and posting; each handle also
waits 30 seconds between posts. The RODDY owner handle is reserved.

Forum tables (`forum_users`, `forum_sessions`, `forum_topics`, `forum_replies`)
are added to the existing protected SQLite database. Checkout tables, receipt
links and private releases remain independent. Back up the database using
SQLite's backup API as described in COMMERCE.md. No extra service, paid provider,
mail credential, external account or environment variable is required. The
frontend uses the catalog's existing HTTPS backend URL.

## Admin

Sign in to `admin.html` with the existing GitHub owner connection, then open
**Community forum**. Publish topics/replies as **RODDY**, hide/restore topics or
individual replies, close/reopen replies, and disable/enable a handle's posting
access. Disabling a handle revokes its sessions; earlier posts remain visible
until separately hidden. Hiding a topic also hides its replies from public read
routes. Owner routes use the same GitHub identity check as inventory and orders,
not a public forum session. Hidden content remains in admin for review.

There is no automated password recovery or self-service editing/deletion in this
first board. The signup dialog explains password recovery; visitors can contact
RODDY privately to request help or content removal. A forum handle is separate
from a Desk Commander Comms account. No email address is collected by the forum.

## Private contact

The modal routes Sales inquiry, New order inquiry and Collaboration to
**sales@roddy.world**. Issue, Concern, Suggestion and Other go to
**support@roddy.world**. Subject/body/name are encoded
into a `mailto:` draft. The button is labelled **Open email app**, and the page
explains that the visitor must review and send it there. It does not claim an
email was sent by the website. **Copy email draft** supports webmail/users without
a configured mail handler; the email address is also a normal direct link.
Email content never enters the forum API, public posts or GitHub catalog.

## Validation

Run `npm test`, `npm run test:backend`, and `npm run build`. Backend tests cover
authentication, password/session storage, persistence, unique/reserved handles,
Origin/rate limits, cooldowns, pagination and owner moderation. Browser checks
use an isolated local database for create/login/post/reply/moderation and verify
literal text rendering, email composition, modal keyboard/focus and mobile fit.
Live deployment smoke tests avoid leaving synthetic public handles/posts.
