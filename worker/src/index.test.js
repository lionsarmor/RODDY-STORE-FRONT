import test from "node:test";
import assert from "node:assert/strict";
import worker, { buildCheckoutParams } from "./index.js";

const env = {
  SITE_URL: "https://roddy.world",
  PRODUCTS_URL: "https://catalog.example/products.json",
  ALLOWED_ORIGINS: "https://roddy.world",
  ADMIN_GITHUB_LOGIN: "lionsarmor",
  STRIPE_SECRET_KEY: "test-placeholder",
};
function catalog(overrides = {}) {
  return {
    settings: {
      checkoutEnabled: true,
      allowPromotionCodes: true,
      shippingCountries: "US,CA",
      shippingRate: 4.95,
    },
    products: [
      {
        id: "game",
        name: "Game",
        active: true,
        status: "available",
        price: 29,
        stock: 5,
        type: "physical",
        ...overrides,
      },
    ],
  };
}
test("checkout uses catalog prices, combines duplicate quantities and charges shipping once", () => {
  const p = buildCheckoutParams(
    catalog(),
    [
      { id: "game", qty: 1, price: 1 },
      { id: "game", qty: 2 },
    ],
    env,
  );
  assert.equal(p.get("line_items[0][quantity]"), "3");
  assert.equal(p.get("line_items[0][price_data][unit_amount]"), "2900");
  assert.equal(
    p.get("shipping_options[0][shipping_rate_data][fixed_amount][amount]"),
    "495",
  );
  assert.equal(p.get("allow_promotion_codes"), "true");
  assert.equal(p.get("metadata[store]"), "roddy");
});
test("duplicate lines cannot bypass stock limits", () => {
  assert.throws(
    () =>
      buildCheckoutParams(
        catalog(),
        [
          { id: "game", qty: 3 },
          { id: "game", qty: 3 },
        ],
        env,
      ),
    /Not enough stock/,
  );
});
test("coming soon, hidden, sold out and unpriced products cannot be purchased", () => {
  for (const p of [
    { status: "coming-soon" },
    { status: "sold-out" },
    { active: false },
    { pricePending: true },
  ]) {
    assert.throws(
      () => buildCheckoutParams(catalog(p), [{ id: "game", qty: 1 }], env),
      /not available/,
    );
  }
});
test("rejects malformed carts and quantities instead of coercing them", () => {
  for (const items of [
    null,
    [],
    [{ id: "game", qty: 0 }],
    [{ id: "game", qty: -1 }],
    [{ id: "game", qty: 1.5 }],
    [{ id: "game", qty: "2" }],
    [null],
    [{ id: "game", qty: 100 }],
  ]) {
    assert.throws(() => buildCheckoutParams(catalog(), items, env));
  }
});
test("digital orders skip shipping and permit unlimited stock", () => {
  const p = buildCheckoutParams(
    catalog({ type: "digital", trackStock: false, stock: 0 }),
    [{ id: "game", qty: 2 }],
    env,
  );
  assert.equal(
    [...p.keys()].some((k) => k.startsWith("shipping")),
    false,
  );
});
test("free products retain zero price", () => {
  const p = buildCheckoutParams(
    catalog({ type: "digital", price: 0, trackStock: false }),
    [{ id: "game", qty: 1 }],
    env,
  );
  assert.equal(p.get("line_items[0][price_data][unit_amount]"), "0");
});
test("checkout switch, invalid prices and unsafe return URLs fail closed", () => {
  const c = catalog();
  c.settings.checkoutEnabled = false;
  assert.throws(
    () => buildCheckoutParams(c, [{ id: "game", qty: 1 }], env),
    /not open/,
  );
  for (const price of [-1, NaN, Infinity, "29"])
    assert.throws(
      () =>
        buildCheckoutParams(catalog({ price }), [{ id: "game", qty: 1 }], env),
      /invalid price/,
    );
  assert.throws(() =>
    buildCheckoutParams(catalog(), [{ id: "game", qty: 1 }], {
      ...env,
      SITE_URL: "javascript:test",
    }),
  );
});
test("CORS rejects untrusted origins", async () => {
  const res = await worker.fetch(
    new Request("https://worker.example/health", {
      headers: { origin: "https://evil.example" },
    }),
    env,
  );
  assert.equal(res.status, 403);
});
test("admin endpoints require authenticated owner identity", async () => {
  let res = await worker.fetch(
    new Request("https://worker.example/admin/orders"),
    env,
  );
  assert.equal(res.status, 401);
  const original = globalThis.fetch;
  globalThis.fetch = async () => Response.json({ login: "someone-else" });
  try {
    res = await worker.fetch(
      new Request("https://worker.example/admin/orders", {
        headers: { authorization: "Bearer placeholder" },
      }),
      env,
    );
    assert.equal(res.status, 403);
  } finally {
    globalThis.fetch = original;
  }
});
test("order verification reports payment status without exposing customer data", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () =>
    Response.json({
      metadata: { store: "roddy" },
      status: "complete",
      payment_status: "paid",
      amount_total: 2900,
      currency: "usd",
      customer_details: { email: "private@example.com" },
    });
  try {
    const res = await worker.fetch(
      new Request("https://worker.example/order?session_id=cs_test_abc123"),
      env,
    );
    const body = await res.json();
    assert.equal(body.paid, true);
    assert.equal(body.customer_details, undefined);
    assert.equal(body.amountTotal, 2900);
  } finally {
    globalThis.fetch = original;
  }
});
test("unpaid or incomplete sessions are never shown as confirmed", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () =>
    Response.json({
      metadata: { store: "roddy" },
      status: "open",
      payment_status: "unpaid",
    });
  try {
    const res = await worker.fetch(
      new Request("https://worker.example/order?session_id=cs_test_abc123"),
      env,
    );
    assert.equal((await res.json()).paid, false);
  } finally {
    globalThis.fetch = original;
  }
});
test("promotion validation runs before creating Stripe objects", async () => {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url) => {
    calls.push(url);
    return Response.json({ login: "lionsarmor" });
  };
  try {
    const res = await worker.fetch(
      new Request("https://worker.example/admin/promotions", {
        method: "POST",
        headers: {
          authorization: "Bearer placeholder",
          "content-type": "application/json",
        },
        body: JSON.stringify({ code: "RODDY10", percent: 101 }),
      }),
      env,
    );
    assert.equal(res.status, 400);
    assert.equal(calls.length, 1);
  } finally {
    globalThis.fetch = original;
  }
});
test("authenticated promotion creation sends the discount and redemption limits to Stripe", async () => {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith("/user")) return Response.json({ login: "lionsarmor" });
    if (url.endsWith("/coupons")) return Response.json({ id: "coupon123" });
    return Response.json({ id: "promo_123", code: "RODDY10" });
  };
  try {
    const res = await worker.fetch(
      new Request("https://worker.example/admin/promotions", {
        method: "POST",
        headers: { authorization: "Bearer placeholder" },
        body: JSON.stringify({
          code: "roddy10",
          percent: 10,
          maxRedemptions: 50,
        }),
      }),
      env,
    );
    assert.equal(res.status, 200);
    assert.equal(
      new URLSearchParams(calls[1].options.body).get("percent_off"),
      "10",
    );
    const params = new URLSearchParams(calls[2].options.body);
    assert.equal(params.get("coupon"), "coupon123");
    assert.equal(params.get("max_redemptions"), "50");
    assert.equal(params.get("code"), "RODDY10");
  } finally {
    globalThis.fetch = original;
  }
});
test("checkout gateway creates a hosted session with an idempotency key", async () => {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return url === env.PRODUCTS_URL
      ? Response.json(catalog())
      : Response.json({ url: "https://checkout.stripe.com/c/pay/example" });
  };
  try {
    const res = await worker.fetch(
      new Request("https://worker.example/checkout", {
        method: "POST",
        body: JSON.stringify({
          items: [{ id: "game", qty: 1 }],
          requestId: "12345678-1234-1234-1234-123456789012",
        }),
      }),
      env,
    );
    assert.equal(res.status, 200);
    assert.equal(
      calls[1].options.headers["Idempotency-Key"],
      "roddy-12345678-1234-1234-1234-123456789012",
    );
    assert.equal(
      (await res.json()).url,
      "https://checkout.stripe.com/c/pay/example",
    );
  } finally {
    globalThis.fetch = original;
  }
});
test("orders return only store sessions and preserve the pagination cursor across other account sessions", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async (url) =>
    url.endsWith("/user")
      ? Response.json({ login: "lionsarmor" })
      : Response.json({
          data: [
            { id: "cs_store", metadata: { store: "roddy" } },
            { id: "cs_other", metadata: {} },
          ],
          has_more: true,
        });
  try {
    const res = await worker.fetch(
      new Request("https://worker.example/admin/orders", {
        headers: { authorization: "Bearer placeholder" },
      }),
      env,
    );
    const body = await res.json();
    assert.equal(body.data.length, 1);
    assert.equal(body.next_cursor, "cs_other");
    assert.equal(body.has_more, true);
  } finally {
    globalThis.fetch = original;
  }
});
