export const SUPPORT_EMAIL = "support@roddy.world";
export const SALES_EMAIL = "sales@roddy.world";
export const CONTACT_EMAIL = SUPPORT_EMAIL;

export function contactRecipient(category) {
  return ["Sales inquiry", "New order inquiry", "Collaboration"].includes(category)
    ? SALES_EMAIL
    : SUPPORT_EMAIL;
}

export function contactMailto(category, subject, name, body) {
  return `mailto:${contactRecipient(category)}?subject=${encodeURIComponent(`[RODDY / ${category}] ${subject.trim()}`)}&body=${encodeURIComponent(`${body.trim()}${name.trim() ? `\n\nFrom: ${name.trim()}` : ""}`)}`;
}

export async function forumRequest(endpoint, path, token = "", body) {
  if (!/^https:\/\//.test(endpoint || "")) throw new Error("The community board is temporarily unavailable. You can still email RODDY.");
  const res = await fetch(endpoint.replace(/\/$/, "") + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {"content-type": "application/json", ...(token ? {authorization: `Bearer ${token}`} : {})},
    ...(body === undefined ? {} : {body: JSON.stringify(body)}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error = new Error(data.error || "The community board could not respond. Please try again.");
    error.status = res.status;
    throw error;
  }
  return data;
}
