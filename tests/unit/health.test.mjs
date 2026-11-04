import assert from 'node:assert/strict';
import { test } from 'node:test';
import { once } from 'node:events';
import { createApp as apiApp } from '../../services/api/src/app.js';
import { createApp as scannerApp } from '../../services/scanner/src/app.js';
import { readPort } from '@ai-security/runtime';

async function request(t, app, path) {
  const server = app.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => new Promise((resolve) => {
    server.close(resolve);
    server.closeAllConnections();
  }));
  return fetch('http://127.0.0.1:' + server.address().port + path);
}

test('API health reports liveness without claiming scans or persistence', async (t) => {
  const response = await request(t, apiApp(), '/api/health');
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.equal(response.headers.get('x-powered-by'), null);
  const body = await response.json();
  assert.equal(body.service, 'api');
  assert.deepEqual(body.capabilities, { scanning: false, persistence: false });
});

test('scanner is explicitly idle before the queue is implemented', async (t) => {
  const response = await request(t, scannerApp(), '/health');
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.service, 'scanner');
  assert.equal(body.capabilities.queueConsumer, false);
});

test('scan endpoints are not exposed as fake successes', async (t) => {
  const response = await request(t, apiApp(), '/api/scans');
  assert.equal(response.status, 404);
  assert.deepEqual(await response.json(), { error: 'not_found' });
});

test('invalid ports fail instead of binding an unexpected interface', () => {
  for (const port of ['', 'abc', '0', '-1', '65536', '1.5']) {
    assert.throws(() => readPort(port, 3001), /Port/);
  }
  assert.equal(readPort(undefined, 3001), 3001);
  assert.equal(readPort('4321', 3001), 4321);
});
