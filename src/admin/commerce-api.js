export async function commerceRequest(endpoint, path, token, body) {
  if (!/^https:\/\//.test(endpoint || ""))
    throw new Error(
      "Add your HTTPS checkout server URL in Checkout settings first.",
    );
  const res = await fetch(endpoint.replace(/\/$/, "") + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "content-type": "application/json",
      ...(token ? { authorization: `Bearer ${token}` } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}
