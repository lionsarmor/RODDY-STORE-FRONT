import assert from "node:assert/strict";
import test from "node:test";
import {SUPPORT_EMAIL, SALES_EMAIL, contactRecipient, contactMailto} from "./forum-api.js";

test("private contact drafts use the exact recipient and encode subject/body safely", () => {
  const url = new URL(contactMailto("Collaboration", "Let's build & share?", "Maker + friend", "Hello!\nAn idea: #retro & games."));
  assert.equal(url.protocol, "mailto:");
  assert.equal(url.pathname, SALES_EMAIL);
  assert.equal(url.searchParams.get("subject"), "[RODDY / Collaboration] Let's build & share?");
  assert.equal(url.searchParams.get("body"), "Hello!\nAn idea: #retro & games.\n\nFrom: Maker + friend");
  assert.equal(url.searchParams.size, 2);
});

test("contact categories route sales and collaborations separately from customer support", () => {
  for (const category of ["Sales inquiry", "New order inquiry", "Collaboration"]) {
    assert.equal(contactRecipient(category), SALES_EMAIL);
    assert.equal(new URL(contactMailto(category, "Question", "", "Hello")).pathname, "sales@roddy.world");
  }
  for (const category of ["Issue", "Existing order", "Concern", "Suggestion", "Other", "", "Unknown"]) {
    assert.equal(contactRecipient(category), SUPPORT_EMAIL);
    assert.equal(new URL(contactMailto(category, "Question", "", "Hello")).pathname, "support@roddy.world");
  }
});
