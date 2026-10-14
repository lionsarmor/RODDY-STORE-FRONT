// Three-way merge: only changes made since the draft's baseline are reapplied.
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const entities = (value) => Array.isArray(value) && value.every((item) =>
  object(item) && typeof item.id === "string") && new Set(value.map((item) => item.id)).size === value.length;

export function mergeCatalog(base, local, remote, choices = {}) {
  const conflicts = [];
  function conflict(path, mine, theirs) {
    if (choices[path] === "local") return mine;
    if (choices[path] === "remote") return theirs;
    conflicts.push({ path, local: mine, remote: theirs });
    return mine;
  }
  function merge(before, mine, theirs, path) {
    if (equal(mine, theirs) || equal(theirs, before)) return mine;
    if (equal(mine, before)) return theirs;
    if (object(before) && object(mine) && object(theirs)) {
      const result = {};
      for (const key of new Set([...Object.keys(before), ...Object.keys(mine), ...Object.keys(theirs)])) {
        const value = merge(before[key], mine[key], theirs[key], path ? `${path}.${key}` : key);
        if (value !== undefined) Object.defineProperty(result, key, { value, enumerable: true, writable: true, configurable: true });
      }
      return result;
    }
    if (["products", "categories", "tags", "keycapProfiles"].includes(path) && [before, mine, theirs].every(entities)) {
      const maps = [before, mine, theirs].map((items) => new Map(items.map((item) => [item.id, item])));
      // Compare the relative order of surviving original entries. Additions and
      // deletions alone should not count as conflicting reorder operations.
      const common = before.map((item) => item.id).filter((id) => maps[1].has(id) && maps[2].has(id));
      const orders = [before, mine, theirs].map((items) => items.map((item) => item.id).filter((id) => common.includes(id)));
      let ordering = equal(orders[1], orders[0]) ? theirs : mine;
      if (!equal(orders[1], orders[0]) && !equal(orders[2], orders[0]) && !equal(orders[1], orders[2])) {
        const orderChoice = conflict(`${path}.order`, mine.map((item) => item.id), theirs.map((item) => item.id));
        ordering = orderChoice === undefined ? mine : orderChoice.map((id) => ({ id }));
      }
      const ids = new Set([...ordering, ...theirs, ...mine, ...before].map((item) => item.id));
      return [...ids].map((id) => merge(...maps.map((map) => map.get(id)), `${path}[${id}]`))
        .filter((item) => item !== undefined);
    }
    // Lists of images/tags and text values are atomic: never silently combine
    // conflicting edits or resurrect a deleted, concurrently edited product.
    return conflict(path, mine, theirs);
  }
  return { catalog: JSON.parse(JSON.stringify(merge(base, local, remote, ""))), conflicts };
}
