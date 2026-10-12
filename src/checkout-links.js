export function checkoutDestination(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" &&
      !url.username &&
      !url.password &&
      ["square.link", "checkout.square.site", "sandbox.square.link"].includes(
        url.hostname,
      )
      ? url.href
      : "";
  } catch {
    return "";
  }
}

export function downloadDestination(value, endpoint) {
  try {
    const url = new URL(value);
    const base = new URL(endpoint.replace(/\/$/, "") + "/");
    return url.protocol === "https:" &&
      !url.username &&
      !url.password &&
      url.origin === base.origin &&
      url.pathname.startsWith(base.pathname + "download/")
      ? url.href
      : "";
  } catch {
    return "";
  }
}
