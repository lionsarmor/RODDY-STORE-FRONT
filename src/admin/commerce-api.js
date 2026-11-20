import { ADMIN_ORIGIN, PRIVATE_ADMIN } from "../config";

export function commerceFetch(endpoint, path, token, options = {}) {
  const base = (endpoint || "").replace(/\/$/, "");
  if (!base.startsWith("https://"))
    throw new Error("Add your HTTPS checkout server URL in Checkout settings first.");
  if (PRIVATE_ADMIN && (base !== ADMIN_ORIGIN || !path.startsWith("/") || path.startsWith("//") || path.includes("\\")))
    throw new Error("Use the trusted RODDY checkout server for staff requests.");
  const headers = new Headers(options.headers);
  if (token) headers.set("authorization", `Bearer ${token}`);
  return fetch(base + path, { ...options, headers, redirect: "error" });
}

export async function commerceRequest(endpoint, path, token, body) {
  const res = await commerceFetch(endpoint, path, token, {
    method: body === undefined ? "GET" : "POST",
    headers: { "content-type": "application/json" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}
