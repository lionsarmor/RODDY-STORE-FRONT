import assert from "node:assert/strict";
import test from "node:test";
import {CONTACT_EMAIL, contactMailto} from "./forum-api.js";

test("private contact drafts use the exact recipient and encode subject/body safely", () => {
  const url = new URL(contactMailto("Collaboration", "Let's build & share?", "Maker + friend", "Hello!\nAn idea: #retro & games."));
  assert.equal(url.protocol, "mailto:");
  assert.equal(url.pathname, CONTACT_EMAIL);
  assert.equal(url.searchParams.get("subject"), "[RODDY / Collaboration] Let's build & share?");
  assert.equal(url.searchParams.get("body"), "Hello!\nAn idea: #retro & games.\n\nFrom: Maker + friend");
  assert.equal(url.searchParams.size, 2);
});
