// Cloudflare Worker: the one server-side piece the storefront needs.
// The static site can't safely hold a Stripe secret key or combine an
// arbitrary cart into one charge on its own — this does exactly that one
// job: take { items: [{ id, qty }] }, re-price it against the live
// products.json (never trust client-supplied prices), and return a Stripe
// Checkout Session URL to redirect to.

function isOriginAllowed(origin, env) {
  const allowList = (env.ALLOWED_ORIGINS || "*")
    .split(",")
    .map((o) => o.trim())
    .filter(Boolean);
  return allowList.includes("*") || allowList.includes(origin);
}

function corsHeaders(request, env) {
  const origin = request.headers.get("origin") || "";
  return {
    "access-control-allow-origin": isOriginAllowed(origin, env) ? origin || "*" : "null",
    "access-control-allow-methods": "POST, OPTIONS",
    "access-control-allow-headers": "content-type",
    vary: "origin",
  };
}

function json(body, status, request, env) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...corsHeaders(request, env) },
  });
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(request, env) });
    }
    if (request.method !== "POST") {
      return json({ error: "Method not allowed" }, 405, request, env);
    }
    if (!env.STRIPE_SECRET_KEY) {
      return json({ error: "Checkout is not configured (missing STRIPE_SECRET_KEY)" }, 500, request, env);
    }
    const origin = request.headers.get("origin") || "";
    if (!isOriginAllowed(origin, env)) {
      return json({ error: "Origin not allowed" }, 403, request, env);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "Invalid JSON body" }, 400, request, env);
    }

    const cartItems = Array.isArray(body?.items) ? body.items : [];
    if (!cartItems.length) {
      return json({ error: "Cart is empty" }, 400, request, env);
    }

    let catalog;
    try {
      const catalogRes = await fetch(env.PRODUCTS_URL, { cf: { cacheTtl: 0 } });
      if (!catalogRes.ok) throw new Error(`catalog fetch failed: ${catalogRes.status}`);
      catalog = await catalogRes.json();
    } catch {
      return json({ error: "Could not load the product catalog" }, 502, request, env);
    }

    const byId = new Map((catalog?.products || []).map((p) => [p.id, p]));
    const lineItems = [];

    for (const raw of cartItems) {
      const id = String(raw?.id ?? "");
      const qty = Math.max(1, Math.min(99, Math.trunc(Number(raw?.qty)) || 0));
      const product = byId.get(id);

      if (!product || !product.active) {
        return json({ error: `"${id}" is no longer available` }, 409, request, env);
      }
      if (typeof product.stock === "number" && product.stock < qty) {
        return json({ error: `Only ${product.stock} left of "${product.name}"` }, 409, request, env);
      }

      lineItems.push({
        name: product.name,
        productId: product.id,
        unitAmount: Math.round(product.price * 100),
        quantity: qty,
      });
    }

    const params = new URLSearchParams();
    params.set("mode", "payment");
    params.set("success_url", `${env.SITE_URL}/order.html?session_id={CHECKOUT_SESSION_ID}`);
    params.set("cancel_url", `${env.SITE_URL}/index.html#/cart`);
    (env.SHIP_TO_COUNTRIES || "US")
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean)
      .forEach((country, i) => params.set(`shipping_address_collection[allowed_countries][${i}]`, country));
    lineItems.forEach((item, i) => {
      params.set(`line_items[${i}][quantity]`, String(item.quantity));
      params.set(`line_items[${i}][price_data][currency]`, "usd");
      params.set(`line_items[${i}][price_data][unit_amount]`, String(item.unitAmount));
      params.set(`line_items[${i}][price_data][product_data][name]`, item.name);
      params.set(`line_items[${i}][price_data][product_data][metadata][product_id]`, item.productId);
    });

    let session;
    try {
      const stripeRes = await fetch("https://api.stripe.com/v1/checkout/sessions", {
        method: "POST",
        headers: {
          authorization: `Bearer ${env.STRIPE_SECRET_KEY}`,
          "content-type": "application/x-www-form-urlencoded",
        },
        body: params.toString(),
      });
      session = await stripeRes.json();
      if (!stripeRes.ok) {
        return json({ error: session?.error?.message || "Stripe rejected the request" }, 502, request, env);
      }
    } catch {
      return json({ error: "Could not reach Stripe" }, 502, request, env);
    }

    return json({ url: session.url }, 200, request, env);
  },
};
