import test from "node:test";
import assert from "node:assert/strict";
import { checkoutDestination, downloadDestination } from "./checkout-links.js";

test("checkout only redirects to Square HTTPS hosts without credentials", () => {
  for (const url of [
    "https://square.link/u/abc",
    "https://checkout.square.site/abc",
    "https://sandbox.square.link/u/abc",
  ]) {
    assert.equal(checkoutDestination(url), url);
  }
  for (const url of [
    "https://square.link.evil.test/u/abc",
    "https://square.link@evil.test/",
    "https://name:password@square.link/",
    "http://square.link/u/abc",
    "javascript:alert(1)",
    "https://checkout.stripe.com/test",
  ]) {
    assert.equal(checkoutDestination(url), "");
  }
});

test("paid download links must belong to the configured backend download path", () => {
  const endpoint = "https://api.example.test/store";
  assert.equal(
    downloadDestination(endpoint + "/download/token", endpoint),
    endpoint + "/download/token",
  );
  assert.equal(downloadDestination(endpoint+'/free-download/token',endpoint),endpoint+'/free-download/token');
  for (const url of [
    "https://evil.test/store/download/token",
    endpoint + "/admin/orders",
    endpoint + "/download/../admin",
    "http://api.example.test/store/download/token",
    "https://secret@api.example.test/store/download/token",
  ]) {
    assert.equal(downloadDestination(url, endpoint), "");
  }
});
