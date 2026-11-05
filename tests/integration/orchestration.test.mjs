import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { createServer, createConnection } from 'node:net';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { setTimeout as delay } from 'node:timers/promises';
import { test } from 'node:test';
import { root } from '../../scripts/local-services.mjs';
import { settings } from '@ai-security/orchestration/settings';
import { openStore } from '@ai-security/orchestration/storage';
import { createQueue } from '@ai-security/orchestration/queue';
import { validateContract } from '@ai-security/contracts';

async function until(read, predicate, timeout = 45000) {
  const deadline = Date.now() + timeout;
  let value;
  while (Date.now() < deadline) {
    value = await read();
    if (predicate(value)) return value;
    await delay(100);
  }
  throw new Error('Condition timed out. Last result: ' + JSON.stringify(value));
}
async function freePort() {
  const server = createServer();
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const port = server.address().port;
  await new Promise(resolve => server.close(resolve));
  return port;
}
async function redisProxy(url) {
  const upstream = new URL(url);
  const sockets = new Set();
  const server = createServer(downstream => {
    const remote = createConnection({ host: upstream.hostname, port: Number(upstream.port || 6379) });
    for (const socket of [remote, downstream]) {
      sockets.add(socket);
      socket.on('error', () => { remote.destroy(); downstream.destroy(); });
      socket.on('close', () => { sockets.delete(socket); remote.destroy(); downstream.destroy(); });
    }
    downstream.pipe(remote).pipe(downstream);
  });
  let port = 0;
  async function start() {
    server.listen(port, '127.0.0.1');
    await once(server, 'listening');
    port = server.address().port;
  }
  async function stop() {
    for (const socket of sockets) socket.destroy();
    if (server.listening) await new Promise(resolve => server.close(resolve));
  }
  await start();
  const proxyUrl = new URL(url);
  proxyUrl.hostname = '127.0.0.1'; proxyUrl.port = String(port);
  return { url: proxyUrl.href, start, stop };
}

test('durable scan orchestration with real MongoDB, Redis and separate service processes', { timeout: 150000 }, async t => {
  const suffix = randomUUID().replaceAll('-', '');
  const config = settings({
    APP_MODE: 'orchestration_test',
    MONGO_URL: process.env.MONGO_URL ?? 'mongodb://127.0.0.1:27017',
    REDIS_URL: process.env.REDIS_URL ?? 'redis://127.0.0.1:6379',
    MONGO_DATABASE: 'integration_' + suffix, QUEUE_NAME: 'integration_' + suffix,
    ALLOWED_TARGETS: 'demo.example.com,second.example.com',
  });
  const store = await openStore(config);
  const directQueue = createQueue(config);
  const proxy = await redisProxy(config.redisUrl);
  const children = new Set();
  async function stop(child) {
    if (child.exitCode !== null || child.signalCode !== null) return;
    const exited = once(child, 'exit');
    child.kill('SIGKILL');
    await exited;
  }
  t.after(async () => {
    await Promise.all([...children].map(stop));
    await proxy.stop();
    await directQueue.queue.obliterate({ force: true });
    await directQueue.close();
    await store.db.dropDatabase();
    await store.close();
  });
  async function service(name, extra = {}) {
    const port = await freePort();
    const child = spawn(process.execPath, ['services/' + name + '/src/index.js'], {
      cwd: root, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, NODE_ENV: 'test', APP_MODE: 'orchestration_test',
        HOST: '127.0.0.1', PORT: String(port), MONGO_URL: config.mongoUrl, REDIS_URL: proxy.url,
        MONGO_DATABASE: config.database, QUEUE_NAME: config.queueName,
        ALLOWED_TARGETS: config.allowedTargets, ...extra },
    });
    children.add(child);
    let logs = '';
    for (const stream of [child.stdout, child.stderr]) stream.on('data', chunk => { logs = (logs + chunk).slice(-6000); });
    const base = 'http://127.0.0.1:' + port;
    try {
      await until(async () => {
        if (child.exitCode !== null) throw new Error(name + ' exited: ' + logs);
        try { return (await fetch(base + '/health')).status; } catch { return 0; }
      }, status => status === 200, 15000);
    } catch (error) { throw new Error(error.message + '\n' + logs, { cause: error }); }
    return { child, base };
  }
  async function request(api, path, body, key) {
    const response = await fetch(api.base + path, {
      method: body ? 'POST' : 'GET', signal: AbortSignal.timeout(7000),
      headers: { 'Content-Type': 'application/json', ...(key ? { 'Idempotency-Key': key } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
    return { status: response.status, location: response.headers.get('location'), body: await response.json() };
  }
  function valid(name, value) {
    const result = validateContract(name, value);
    assert.equal(result.valid, true, JSON.stringify(result.errors));
  }
  let api = await service('api');
  const otherApi = await service('api');
  let worker;
  let asset;
  let second;
  let originalScan;
  await t.test('exact allowlist and concurrent target creation across two API processes', async () => {
    assert.equal((await request(api, '/api/assets', { hostname: 'forbidden.example' })).status, 403);
    const results = await Promise.all(Array.from({ length: 8 }, (_, i) => request(i % 2 ? api : otherApi, '/api/assets', { hostname: 'HTTPS://DEMO.EXAMPLE.COM/' })));
    for (const result of results) { assert.equal(result.status, 201); valid('Asset', result.body); }
    assert.equal(new Set(results.map(r => r.body.id)).size, 1);
    assert.equal(await store.assets.countDocuments(), 1);
    asset = results[0].body;
    second = (await request(api, '/api/assets', { hostname: 'second.example.com' })).body;
    const firstPage = (await request(api, '/api/assets?limit=1')).body;
    const nextPage = (await request(api, '/api/assets?limit=1&cursor=' + firstPage.nextCursor)).body;
    valid('AssetPage', firstPage); valid('AssetPage', nextPage);
    assert.notEqual(firstPage.items[0].id, nextPage.items[0].id);
    assert.equal(nextPage.nextCursor, null);
  });
  await t.test('concurrent retries create one durable request and conflicting key reuse is rejected', async () => {
    const results = await Promise.all(Array.from({ length: 8 }, (_, i) => request(i % 2 ? api : otherApi, '/api/scans', { assetId: asset.id }, 'same-request')));
    assert.equal(new Set(results.map(r => r.body.id)).size, 1);
    for (const result of results) {
      assert.equal(result.status, 202); valid('Scan', result.body);
      assert.equal(result.location, '/api/scans/' + result.body.id);
      assert.equal(result.body.executionMode, 'orchestration_test');
    }
    assert.equal(await store.scans.countDocuments(), 1);
    assert.equal((await request(api, '/api/scans', { assetId: second.id }, 'same-request')).status, 409);
    originalScan = results[0].body;
  });
  await t.test('accepted state survives API restarts and completes as an explicit partial test', async () => {
    await stop(api.child); await stop(otherApi.child);
    api = await service('api');
    assert.equal((await request(api, '/api/scans/' + originalScan.id)).body.status, 'queued');
    worker = await service('scanner');
    const result = await until(async () => (await request(api, '/api/scans/' + originalScan.id)).body, value => value.status === 'partial');
    valid('Scan', result);
    assert.ok(result.sources.every(source => source.status === 'unavailable'));
    assert.equal((await store.scans.findOne({ _id: result.id })).resultWrites, 1);
    assert.equal((await request(api, '/ready')).status, 200);
  });
  await t.test('a repeated queue delivery cannot commit duplicate results', async () => {
    await until(() => directQueue.queue.getJob(originalScan.id).then(job => job.getState()), value => value === 'completed');
    await (await directQueue.queue.getJob(originalScan.id)).remove();
    await directQueue.queue.add('orchestration_test', { scanId: originalScan.id }, { jobId: originalScan.id });
    await until(() => directQueue.queue.getJob(originalScan.id).then(job => job.getState()), value => value === 'completed');
    assert.equal((await store.scans.findOne({ _id: originalScan.id })).resultWrites, 1);
  });
  await t.test('a killed worker is replaced and its stalled request is recovered', async () => {
    await stop(worker.child);
    worker = await service('scanner', { TEST_WORK_DELAY_MS: '30000' });
    const scan = (await request(api, '/api/scans', { assetId: asset.id }, 'worker-crash')).body;
    await until(() => store.getScan(scan.id), value => value.status === 'running');
    await stop(worker.child);
    worker = await service('scanner');
    const result = await until(() => store.getScan(scan.id), value => value.status === 'partial');
    assert.ok(result.attempt >= 2);
    assert.equal((await store.scans.findOne({ _id: scan.id })).resultWrites, 1);
  });
  await t.test('queue outage during acceptance and API restart preserves the request for reconciliation', async () => {
    await stop(worker.child);
    await proxy.stop();
    await until(async () => (await request(api, '/ready')).status, status => status === 503);
    const accepted = await request(api, '/api/scans', { assetId: asset.id }, 'offline-queue');
    assert.equal(accepted.status, 202);
    assert.equal(accepted.body.status, 'queued');
    await stop(api.child);
    api = await service('api');
    const replay = await request(api, '/api/scans', { assetId: asset.id }, 'offline-queue');
    assert.equal(replay.body.id, accepted.body.id);
    await proxy.start();
    worker = await service('scanner');
    await until(() => store.getScan(accepted.body.id), value => value.status === 'partial');
    assert.equal((await store.scans.findOne({ _id: accepted.body.id })).resultWrites, 1);
  });
  await t.test('worker checks authorization again before processing a queued request', async () => {
    await stop(worker.child);
    const scan = (await request(api, '/api/scans', { assetId: asset.id }, 'revoked-target')).body;
    worker = await service('scanner', { ALLOWED_TARGETS: '' });
    const result = await until(() => store.getScan(scan.id), value => value.status === 'failed');
    valid('Scan', result);
    assert.match(result.sources[0].reason, /authorized/);
  });
});
