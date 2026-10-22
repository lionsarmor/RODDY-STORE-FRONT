import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {runInNewContext} from 'node:vm';

for (const entry of ['index.html', 'admin.html', 'order.html']) {
  test(`${entry} upgrades insecure production visits before loading the app`, () => {
    const html = readFileSync(new URL('../' + entry, import.meta.url), 'utf8');
    const guard = html.match(/<script id="enforce-https">([\s\S]*?)<\/script>/);
    assert.ok(guard);
    assert.ok(guard.index < html.indexOf('<link'));
    assert.ok(guard.index < html.indexOf('type="module"'));
    for (const host of ['roddy.world', 'www.roddy.world']) {
      for (const suffix of ['/product/buddy/?from=instagram', '/?fbclid=test#/product/orbit', '/order.html#session_id=private-reference']) {
        const location = new URL('http://' + host + suffix);
        let destination;
        location.replace = value => { destination = value; };
        runInNewContext(guard[1], {location});
        assert.equal(destination, 'https://roddy.world' + suffix);
      }
    }
    for (const address of ['https://roddy.world/shop/', 'http://localhost:5173/', 'http://127.0.0.1:4173/', 'http://roddy.world.example/']) {
      const location = new URL(address);
      location.replace = () => { assert.fail('Secure visits and other hosts must remain unchanged'); };
      runInNewContext(guard[1], {location});
    }
  });
}
