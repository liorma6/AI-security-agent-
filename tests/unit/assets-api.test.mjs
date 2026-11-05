import assert from 'node:assert/strict';
import { once } from 'node:events';
import { test } from 'node:test';
import { createApp } from '../../services/api/src/app.js';
import { validateContract } from '@ai-security/contracts';

async function fixture(t, overrides = {}) {
  const store = {
    ping: async () => true,
    createAsset: async hostname => ({ hostname }),
    listAssets: async () => ({ items: [], nextCursor: null }),
    getAsset: async () => null,
    ...overrides,
  };
  const app = createApp({ store, queue: { ping: async () => true }, allowedTargets: 'example.com' });
  const server = app.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => new Promise(resolve => { server.close(resolve); server.closeAllConnections(); }));
  return (path, body, method = 'POST') => fetch('http://127.0.0.1:' + server.address().port + path, {
    method, headers: { 'Content-Type': 'application/json' },
    body: method === 'GET' ? undefined : JSON.stringify(body),
  });
}
test('API rejects unauthorized targets, extra authority fields and malformed input', async t => {
  let writes = 0;
  const request = await fixture(t, { createAsset: async () => { writes++; } });
  for (const [body, status] of [
    [{ hostname: 'forbidden.example' }, 403],
    [{ hostname: 'example.com', authorization: { scope: 'lab' } }, 400],
    [{ hostname: 'http://127.0.0.1/' }, 400],
    [null, 400],
  ]) {
    const response = await request('/api/assets', body);
    assert.equal(response.status, status);
    assert.equal(validateContract('ApiError', await response.json()).valid, true);
  }
  assert.equal(writes, 0);
});
test('API normalizes allowed input before persistence', async t => {
  const request = await fixture(t);
  const response = await request('/api/assets', { hostname: 'HTTPS://EXAMPLE.COM/' });
  assert.equal(response.status, 201);
  assert.equal((await response.json()).hostname, 'example.com');
});
test('pagination rejects invalid sizes and repeated cursor values', async t => {
  const request = await fixture(t);
  for (const query of ['limit=0', 'limit=101', 'limit=1&limit=2', 'limit=1.5', 'cursor=bad', 'other=x',
    'cursor=00000000-0000-4000-8000-000000000001&cursor=00000000-0000-4000-8000-000000000002']) {
    assert.equal((await request('/api/assets?' + query, null, 'GET')).status, 400);
  }
});
test('storage errors have a bounded public response', async t => {
  const request = await fixture(t, { createAsset: async () => { throw new Error('private connection string'); } });
  const response = await request('/api/assets', { hostname: 'example.com' });
  assert.equal(response.status, 503);
  const error = await response.json();
  assert.equal(error.error.code, 'service_unavailable');
  assert.doesNotMatch(JSON.stringify(error), /private connection/);
});
test('readiness distinguishes unavailable storage from liveness', async t => {
  const request = await fixture(t, { ping: async () => { throw new Error('offline'); } });
  const response = await request('/ready', null, 'GET');
  assert.equal(response.status, 503);
  const body = await response.json();
  assert.equal(validateContract('Readiness', body).valid, true);
  assert.deepEqual(body.dependencies, { mongo: false, redis: true });
  assert.equal((await request('/health', null, 'GET')).status, 200);
});
