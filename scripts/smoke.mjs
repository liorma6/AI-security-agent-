import assert from 'node:assert/strict';
import { setTimeout as delay } from 'node:timers/promises';
import { localPorts, startServices } from './local-services.mjs';

async function waitFor(url) {
  const deadline = Date.now() + 45000;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(2000) });
      if (!response.ok) throw new Error(url + ': HTTP ' + response.status);
      return response;
    } catch (error) {
      lastError = error;
      await delay(200);
    }
  }
  throw lastError;
}

let services;
try {
  const ports = localPorts();
  if (!process.argv.includes('--stack')) services = await startServices({ preview: true, ports });
  const checks = async () => {
    for (const [service, path] of [['api', '/health'], ['scanner', '/health'], ['ml', '/health']]) {
      const response = await waitFor('http://127.0.0.1:' + ports[service] + path);
      const data = await response.json();
      assert.equal(data.service, service);
      assert.equal(data.status, 'ok');
      const active = service !== 'ml' && ['orchestration_test', 'collection'].includes(data.mode);
      const collection = active && data.mode === 'collection';
      assert.equal(data.stage, collection ? 4 : (active ? 3 : 1));
      assert.equal(data.capabilities.scanning ?? data.capabilities.inference, collection);
      if (active) {
        const readiness = await waitFor('http://127.0.0.1:' + ports[service] + '/ready');
        assert.equal((await readiness.json()).status, 'ready');
      }
      process.stdout.write('PASS ' + service + ' health and honest capabilities\n');
    }
    const html = await (await waitFor('http://127.0.0.1:' + ports.web)).text();
    assert.match(html, /<div id="root"/);
    const proxied = await (await waitFor('http://127.0.0.1:' + ports.web + '/api/health')).json();
    assert.equal(proxied.service, 'api');
    process.stdout.write('PASS web build and same-origin API proxy\n');
  };
  await Promise.race([checks(), ...(services ? [services.failed.then((error) => { throw error; })] : [])]);
} catch (error) {
  process.stderr.write(error.stack + '\n');
  process.exitCode = 1;
} finally {
  await services?.stop();
}
