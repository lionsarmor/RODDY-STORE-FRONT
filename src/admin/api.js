/* GitHub Contents API — reads and writes public/data/products.json directly
   from the browser using a user-supplied personal access token. No backend.
   Note: this is the path in the repo's source tree (what the GitHub API
   operates on), not the built site's URL — Vite copies public/* to the dist
   root, so the deployed site fetches it from /data/products.json, but the
   Contents API needs the real repo path. */
const FILE_PATH = "public/data/products.json";

export const DEFAULT_CATEGORIES = [
  { id: "games", name: "Games", code: "RODDY GAMES" },
  { id: "computers", name: "Computers", code: "RODDY COMPUTERS" },
  { id: "pocket", name: "Pocket", code: "RODDY POCKET" },
  { id: "labs", name: "Labs", code: "RODDY KITS" },
  { id: "objects", name: "Objects", code: "RODDY OBJECTS" },
];

function utf8ToBase64(str) {
  const bytes = new TextEncoder().encode(str);
  let binary = "";
  bytes.forEach((b) => {
    binary += String.fromCharCode(b);
  });
  return btoa(binary);
}

function base64ToUtf8(b64) {
  const binary = atob(b64.replace(/\n/g, ""));
  const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

function ghHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
  };
}

function contentsUrl(owner, repo, path = FILE_PATH) {
  return `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;
}

export async function fetchCatalog({ owner, repo, branch, token }) {
  const res = await fetch(`${contentsUrl(owner, repo)}?ref=${encodeURIComponent(branch)}`, {
    headers: ghHeaders(token),
  });

  if (res.status === 404) {
    return { sha: null, catalog: { categories: DEFAULT_CATEGORIES, products: [] } };
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || `GitHub GET failed (${res.status})`);
  }

  const json = await res.json();
  return { sha: json.sha, catalog: JSON.parse(base64ToUtf8(json.content)) };
}

export async function saveCatalog({ owner, repo, branch, token, sha }, catalog) {
  const body = {
    message: `Update inventory via RODDY admin (${new Date().toISOString().slice(0, 19)}Z)`,
    content: utf8ToBase64(`${JSON.stringify(catalog, null, 2)}\n`),
    branch,
  };
  if (sha) body.sha = sha;

  const res = await fetch(contentsUrl(owner, repo), {
    method: "PUT",
    headers: { ...ghHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 409) {
      throw new Error(
        "Someone else changed this file since you loaded it. Reload from GitHub and re-apply your edits."
      );
    }
    throw new Error(json.message || `GitHub PUT failed (${res.status})`);
  }
  return json.content ? json.content.sha : sha;
}

/** Uploads (or overwrites, if a file already exists at that path) a binary
    file — used for product photos, committed alongside data/products.json. */
export async function uploadFile({ owner, repo, branch, token }, path, base64Content) {
  const existing = await fetch(`${contentsUrl(owner, repo, path)}?ref=${encodeURIComponent(branch)}`, {
    headers: ghHeaders(token),
  });
  let sha = null;
  if (existing.status === 200) {
    sha = (await existing.json()).sha;
  } else if (existing.status !== 404) {
    const body = await existing.json().catch(() => ({}));
    throw new Error(body.message || `GitHub GET failed (${existing.status})`);
  }

  const body = {
    message: `Update product photo via RODDY admin (${new Date().toISOString().slice(0, 19)}Z)`,
    content: base64Content,
    branch,
  };
  if (sha) body.sha = sha;

  const res = await fetch(contentsUrl(owner, repo, path), {
    method: "PUT",
    headers: { ...ghHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.message || `GitHub PUT failed (${res.status})`);
  return json;
}

/** Lists photo files already committed anywhere under public/img/ (SVGs —
    the brand pack — are excluded), so admin can point a product at an image
    that was placed in the repo directly instead of uploaded through here. */
export async function listRepoImages({ owner, repo, branch, token }) {
  const res = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/git/trees/${encodeURIComponent(branch)}?recursive=1`,
    { headers: ghHeaders(token) }
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || `GitHub GET failed (${res.status})`);
  }
  const json = await res.json();
  return (json.tree || [])
    .filter((item) => item.type === "blob" && /^public\/img\/.*\.(jpe?g|png|webp|gif)$/i.test(item.path))
    .map((item) => item.path.replace(/^public\//, ""))
    .sort();
}
