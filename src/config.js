// URL of the Cloudflare Worker that turns a cart into a real Stripe Checkout
// Session (see /worker). Deploy the worker (`npm run deploy` inside worker/),
// then paste its workers.dev (or custom) URL here.
export const CHECKOUT_ENDPOINT = "https://roddy-checkout.YOUR-SUBDOMAIN.workers.dev";
