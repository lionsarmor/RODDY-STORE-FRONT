// RODDY commerce gateway. Public catalog data controls the store; secrets stay here.
class HttpError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.status = status;
  }
}
function allowed(request, env) {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  return (env.ALLOWED_ORIGINS || "")
    .split(",")
    .map((s) => s.trim())
    .includes(origin);
}
function json(data, status, request, env) {
  const origin = request.headers.get("origin") || "";
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json",
      "cache-control": "no-store",
      "access-control-allow-origin": allowed(request, env) ? origin : "null",
      "access-control-allow-methods": "GET, POST, OPTIONS",
      "access-control-allow-headers": "content-type, authorization",
      "x-content-type-options": "nosniff",
      vary: "Origin",
    },
  });
}
async function bodyJson(request) {
  const raw = await request.text();
  if (raw.length > 24000) throw new HttpError("Request too large.", 413);
  try {
    return JSON.parse(raw);
  } catch {
    throw new HttpError("Invalid JSON body.");
  }
}
async function stripe(env, path, params, idempotencyKey) {
  if (!env.STRIPE_SECRET_KEY)
    throw new HttpError("Stripe is not connected yet.", 503);
  const res = await fetch("https://api.stripe.com/v1" + path, {
    method: params ? "POST" : "GET",
    headers: {
      authorization: `Bearer ${env.STRIPE_SECRET_KEY}`,
      "content-type": "application/x-www-form-urlencoded",
      "Stripe-Version": "2024-06-20",
      ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
    },
    ...(params ? { body: new URLSearchParams(params).toString() } : {}),
  });
  const data = await res.json();
  if (!res.ok)
    throw new HttpError(data.error?.message || "Stripe request failed.", 502);
  return data;
}
async function adminAuth(request, env) {
  const token = request.headers.get("authorization") || "";
  if (!token.startsWith("Bearer ") || !env.ADMIN_GITHUB_LOGIN)
    throw new HttpError("Sign in with the store owner GitHub token.", 401);
  const res = await fetch("https://api.github.com/user", {
    headers: {
      Authorization: token,
      Accept: "application/vnd.github+json",
      "User-Agent": "RODDY-Control-Desk",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });
  if (!res.ok)
    throw new HttpError("GitHub sign-in could not be verified.", 401);
  const user = await res.json();
  if (user.login?.toLowerCase() !== env.ADMIN_GITHUB_LOGIN.toLowerCase())
    throw new HttpError(
      "Only the configured store owner can manage commerce.",
      403,
    );
}
async function loadCatalog(env) {
  try {
    const res = await fetch(env.PRODUCTS_URL, {
      cache: "no-store",
      cf: { cacheTtl: 0 },
    });
    if (!res.ok) throw new Error();
    return await res.json();
  } catch {
    throw new HttpError("Could not load the product catalog.", 502);
  }
}
export function buildCheckoutParams(catalog, items, env) {
  const settings = catalog.settings || {};
  if (!settings.checkoutEnabled)
    throw new HttpError("Online checkout is not open yet.", 503);
  if (!Array.isArray(items) || !items.length || items.length > 30)
    throw new HttpError("Your cart must contain between 1 and 30 items.");
  const combined = new Map();
  for (const item of items) {
    if (
      !item ||
      typeof item.id !== "string" ||
      !Number.isInteger(item.qty) ||
      item.qty < 1 ||
      item.qty > 99
    )
      throw new HttpError("Invalid item or quantity.");
    combined.set(item.id, (combined.get(item.id) || 0) + item.qty);
  }
  const products = new Map((catalog.products || []).map((p) => [p.id, p]));
  const lineItems = [];
  for (const [id, quantity] of combined) {
    const p = products.get(id);
    if (
      !p ||
      !p.active ||
      p.pricePending ||
      ["coming-soon", "sold-out"].includes(p.status)
    )
      throw new HttpError(`"${p?.name || id}" is not available to buy.`, 409);
    if (quantity > 99)
      throw new HttpError("Maximum quantity is 99 per product.");
    if (
      p.trackStock !== false &&
      (!Number.isInteger(p.stock) || p.stock < quantity)
    )
      throw new HttpError(
        `Not enough stock for "${p.name}". Please update your cart.`,
        409,
      );
    if (
      typeof p.price !== "number" ||
      !Number.isFinite(p.price) ||
      p.price < 0 ||
      Math.round(p.price * 100) > 99999999
    )
      throw new HttpError(
        "This product has an invalid price. Please contact the store.",
        409,
      );
    lineItems.push({ product: p, quantity });
  }
  if (!/^https:\/\//.test(env.SITE_URL || ""))
    throw new HttpError("Store return URL is not configured.", 503);
  const siteUrl = env.SITE_URL.replace(/\/$/, "");
  const params = new URLSearchParams({
    mode: "payment",
    success_url: siteUrl + "/order.html?session_id={CHECKOUT_SESSION_ID}",
    cancel_url: siteUrl + "/index.html#/cart?canceled=1",
    "metadata[store]": "roddy",
    "automatic_tax[enabled]": String(!!settings.automaticTax),
    allow_promotion_codes: String(!!settings.allowPromotionCodes),
  });
  if (lineItems.some(({ product }) => product.type !== "digital")) {
    const countries = (
      settings.shippingCountries ||
      env.SHIP_TO_COUNTRIES ||
      "US"
    )
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean);
    if (!countries.length || countries.some((c) => !/^[A-Z]{2}$/.test(c)))
      throw new HttpError(
        "Shipping countries are not configured correctly.",
        503,
      );
    countries.forEach((c, i) =>
      params.set(`shipping_address_collection[allowed_countries][${i}]`, c),
    );
    const shipping = settings.shippingRate ?? 0;
    if (
      typeof shipping !== "number" ||
      !Number.isFinite(shipping) ||
      shipping < 0
    )
      throw new HttpError("Shipping price is not configured correctly.", 503);
    params.set("shipping_options[0][shipping_rate_data][type]", "fixed_amount");
    params.set(
      "shipping_options[0][shipping_rate_data][fixed_amount][amount]",
      String(Math.round(shipping * 100)),
    );
    params.set(
      "shipping_options[0][shipping_rate_data][fixed_amount][currency]",
      "usd",
    );
    params.set(
      "shipping_options[0][shipping_rate_data][display_name]",
      settings.shippingLabel || "Standard shipping",
    );
  }
  lineItems.forEach(({ product: p, quantity }, i) => {
    params.set(`line_items[${i}][quantity]`, String(quantity));
    params.set(`line_items[${i}][price_data][currency]`, "usd");
    params.set(
      `line_items[${i}][price_data][unit_amount]`,
      String(Math.round(p.price * 100)),
    );
    params.set(`line_items[${i}][price_data][product_data][name]`, p.name);
    params.set(
      `line_items[${i}][price_data][product_data][metadata][product_id]`,
      p.id,
    );
  });
  return params;
}
async function adminRoute(request, env, url) {
  await adminAuth(request, env);
  if (url.pathname === "/admin/orders" && request.method === "GET") {
    const after = url.searchParams.get("after");
    if (after && !/^cs_[A-Za-z0-9_]+$/.test(after))
      throw new HttpError("Invalid order cursor.");
    const data = await stripe(
      env,
      "/checkout/sessions?limit=25" +
        (after ? "&starting_after=" + encodeURIComponent(after) : ""),
    );
    return {
      data: data.data
        .filter((s) => s.metadata?.store === "roddy")
        .map((s) => ({
          id: s.id,
          created: s.created,
          amount_total: s.amount_total,
          currency: s.currency,
          payment_status: s.payment_status,
          customer_details: { email: s.customer_details?.email || "" },
        })),
      has_more: data.has_more,
      next_cursor: data.data.at(-1)?.id || "",
    };
  }
  if (url.pathname === "/admin/promotions" && request.method === "GET") {
    const data = await stripe(env, "/promotion_codes?limit=100");
    return {
      data: data.data
        .filter((p) => p.metadata?.store === "roddy")
        .map((p) => ({
          id: p.id,
          code: p.code,
          active: p.active,
          percent_off: p.coupon?.percent_off,
          times_redeemed: p.times_redeemed,
          max_redemptions: p.max_redemptions,
          expires_at: p.expires_at,
        })),
    };
  }
  if (url.pathname === "/admin/promotions" && request.method === "POST") {
    const body = await bodyJson(request);
    const code = String(body.code || "")
      .trim()
      .toUpperCase();
    if (!/^[A-Z0-9]{1,40}$/.test(code))
      throw new HttpError("Use 1–40 letters and numbers for the promo code.");
    if (
      typeof body.percent !== "number" ||
      !Number.isFinite(body.percent) ||
      body.percent < 1 ||
      body.percent > 100
    )
      throw new HttpError("Discount must be from 1 to 100 percent.");
    if (
      body.maxRedemptions != null &&
      (!Number.isInteger(body.maxRedemptions) || body.maxRedemptions < 1)
    )
      throw new HttpError("Maximum uses must be a positive whole number.");
    const expires = body.expiresAt
      ? Math.floor(Date.parse(body.expiresAt) / 1000)
      : null;
    if (
      body.expiresAt &&
      (!Number.isFinite(expires) || expires <= Date.now() / 1000)
    )
      throw new HttpError("Expiration must be in the future.");
    // Validate all inputs before creating the coupon and its customer-facing code.
    const coupon = await stripe(env, "/coupons", {
      percent_off: String(body.percent),
      duration: "once",
      name: "RODDY " + code,
      "metadata[store]": "roddy",
    });
    const params = { coupon: coupon.id, code, "metadata[store]": "roddy" };
    if (body.maxRedemptions)
      params.max_redemptions = String(body.maxRedemptions);
    if (expires) params.expires_at = String(expires);
    return await stripe(env, "/promotion_codes", params);
  }
  const match = url.pathname.match(
    /^\/admin\/promotions\/(promo_[A-Za-z0-9]+)$/,
  );
  if (match && request.method === "POST") {
    const body = await bodyJson(request);
    if (typeof body.active !== "boolean")
      throw new HttpError("Active must be true or false.");
    const p = await stripe(env, "/promotion_codes/" + match[1]);
    if (p.metadata?.store !== "roddy")
      throw new HttpError("This promotion does not belong to RODDY.", 403);
    return await stripe(env, "/promotion_codes/" + match[1], {
      active: String(body.active),
    });
  }
  throw new HttpError("Not found.", 404);
}
export default {
  async fetch(request, env) {
    try {
      if (!allowed(request, env))
        throw new HttpError("Origin not allowed.", 403);
      if (request.method === "OPTIONS")
        return new Response(null, {
          status: 204,
          headers: json({}, 200, request, env).headers,
        });
      const url = new URL(request.url);
      let result;
      if (url.pathname === "/health" && request.method === "GET") {
        if (env.STRIPE_SECRET_KEY) await stripe(env, "/balance");
        result = {
          ok: true,
          stripeConfigured: !!env.STRIPE_SECRET_KEY,
          mode: env.STRIPE_SECRET_KEY?.startsWith("sk_live_") ? "live" : "test",
        };
      } else if (url.pathname.startsWith("/admin/")) {
        result = await adminRoute(request, env, url);
      } else if (url.pathname === "/order" && request.method === "GET") {
        const id = url.searchParams.get("session_id");
        if (!/^cs_(test_|live_)?[A-Za-z0-9]+$/.test(id || ""))
          throw new HttpError("Invalid order reference.");
        const session = await stripe(env, "/checkout/sessions/" + id);
        if (session.metadata?.store !== "roddy")
          throw new HttpError("Order not found.", 404);
        result = {
          status: session.status,
          paid:
            session.status === "complete" &&
            ["paid", "no_payment_required"].includes(session.payment_status),
          amountTotal: session.amount_total,
          currency: session.currency,
        };
      } else if (
        ["/", "/checkout"].includes(url.pathname) &&
        request.method === "POST"
      ) {
        const body = await bodyJson(request);
        const catalog = await loadCatalog(env);
        const params = buildCheckoutParams(catalog, body.items, env);
        const requestId = body.requestId;
        if (requestId && !/^[a-zA-Z0-9-]{16,80}$/.test(requestId))
          throw new HttpError("Invalid checkout request ID.");
        const session = await stripe(
          env,
          "/checkout/sessions",
          params,
          requestId ? "roddy-" + requestId : undefined,
        );
        if (!session.url?.startsWith("https://checkout.stripe.com/"))
          throw new HttpError("Stripe did not return a checkout URL.", 502);
        result = { url: session.url };
      } else throw new HttpError("Not found.", 404);
      return json(result, 200, request, env);
    } catch (e) {
      return json(
        {
          error:
            e instanceof HttpError
              ? e.message
              : "The commerce service is temporarily unavailable. Please try again.",
        },
        e.status || 502,
        request,
        env,
      );
    }
  },
};
