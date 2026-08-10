/* GitHub Contents API — reads and writes data/products.json directly from
   the browser using a user-supplied personal access token. No backend. */

const FILE_PATH = "data/products.json";

export const DEFAULT_CATEGORIES = [
  { id: "games", name: "Games", code: "RODDY GAMES" },
  { id: "computers", name: "Computers", code: "RODDY COMPUTERS" },
  { id: "pocket", name: "Pocket", code: "RODDY POCKET" },
  { id: "labs", name: "Labs", code: "RODDY LABS" },
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

function contentsUrl(owner, repo) {
  return `https://api.github.com/repos/${owner}/${repo}/contents/${FILE_PATH}`;
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
