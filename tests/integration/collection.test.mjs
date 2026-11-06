import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { once } from 'node:events';
import { setTimeout as delay } from 'node:timers/promises';
import { test } from 'node:test';
import { createApp } from '../../services/api/src/app.js';
import { openStore } from '@ai-security/orchestration/storage';
import { settings } from '@ai-security/orchestration/settings';
import { createQueue, startDispatcher, startWorker } from '@ai-security/orchestration/queue';
import { createCollector } from '@ai-security/orchestration/collector';
import { validateContract } from '@ai-security/contracts';
import { startCollectorLab } from '../fixtures/tls/collector-harness.mjs';

async function until(read, predicate, timeout = 15000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const value = await read();
    if (predicate(value)) return value;
    await delay(50);
  }
  throw new Error('Timed out waiting for the stored collection result.');
}

test('collection commits actual TLS evidence through API, Redis worker and MongoDB', { timeout: 45000 }, async t => {
  const suffix = randomUUID().replaceAll('-', '');
  const config = settings({ APP_MODE: 'collection', ALLOWED_TARGETS: 'valid.lab.test',
    MONGO_URL: process.env.MONGO_URL ?? 'mongodb://127.0.0.1:27017',
    REDIS_URL: process.env.REDIS_URL ?? 'redis://127.0.0.1:6379',
    MONGO_DATABASE: 'collection_' + suffix, QUEUE_NAME: 'collection_' + suffix });
  const lab = await startCollectorLab();
  t.after(lab.stop);
  const store = await openStore(config);
  const queue = createQueue(config);
  await queue.queue.waitUntilReady();
  const dispatcher = startDispatcher(store, queue.queue, { intervalMs: 100 });
  const collector = createCollector(config, { policy: lab.policy, trustProfiles: lab.trustProfiles,
    roots: () => [lab.url('sni'), lab.url('redirect')] });
  let active = 0;
  let maximumActive = 0;
  const collect = async (...args) => {
    active++;
    maximumActive = Math.max(maximumActive, active);
    try { await delay(50); return await collector(...args); }
    finally { active--; }
  };
  const workers = [startWorker(store, config, { collect }), startWorker(store, config, { collect })];
  let server;
  function listen() {
    server = createApp({ store, queue, mode: config.mode, allowedTargets: config.allowedTargets }).listen(0, '127.0.0.1');
    return once(server, 'listening');
  }
  async function stopServer() {
    await new Promise(done => { server.close(done); server.closeAllConnections(); });
  }
  t.after(async () => {
    await stopServer();
    await dispatcher.close();
    await Promise.all(workers.map(worker => worker.close()));
    await queue.queue.obliterate({ force: true });
    await queue.close();
    await store.db.dropDatabase();
    await store.close();
  });
  await listen();
  async function request(path, body, key) {
    const response = await fetch('http://127.0.0.1:' + server.address().port + path, {
      method: body ? 'POST' : 'GET', signal: AbortSignal.timeout(5000),
      headers: { 'Content-Type': 'application/json', ...(key ? { 'Idempotency-Key': key } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
    return { status: response.status, body: await response.json() };
  }
  const asset = (await request('/api/assets', { hostname: 'valid.lab.test' })).body;
  let scan;
  let evidence;
  await t.test('accepted collection produces authenticated, schema-valid observations over actual sockets', async () => {
    const accepted = await request('/api/scans', { assetId: asset.id }, 'collection-request');
    assert.equal(accepted.status, 202);
    scan = accepted.body;
    assert.equal(scan.executionMode, 'collection');
    await until(() => store.getScan(scan.id), record => record.status === 'partial');
    evidence = (await request('/api/scans/' + scan.id + '/observations')).body;
    assert.equal(validateContract('ObservationList', evidence).valid, true);
    assert.ok(evidence.items.length >= 4);
    const tls = evidence.items.find(item => item.source === 'tls');
    assert.equal(tls.evidence.authorized, true);
    assert.equal(tls.endpoint.certificateSha256, tls.evidence.certificate.sha256);
    assert.equal(evidence.items.at(-1).evidence.authenticated, true);
    assert.equal((await store.scans.findOne({ _id: scan.id })).resultWrites, 1);
    const publicScan = (await request('/api/scans/' + scan.id)).body;
    assert.equal(validateContract('Scan', publicScan).valid, true);
    assert.equal(Object.hasOwn(publicScan, 'collectedObservations'), false);
    assert.equal((await request('/api/health')).body.stage, 4);
  });
  await t.test('API restart and repeated delivery retain exactly the committed evidence', async () => {
    await stopServer(); await listen();
    assert.deepEqual((await request('/api/scans/' + scan.id + '/observations')).body, evidence);
    await until(() => queue.queue.getJob(scan.id).then(job => job.getState()), state => state === 'completed');
    await (await queue.queue.getJob(scan.id)).remove();
    await queue.queue.add('collection', { scanId: scan.id }, { jobId: scan.id });
    await until(() => queue.queue.getJob(scan.id).then(job => job.getState()), state => state === 'completed');
    assert.deepEqual((await store.getObservations(scan.id)), evidence);
    assert.equal((await store.scans.findOne({ _id: scan.id })).resultWrites, 1);
  });
  await t.test('target leases arbitrate workers and recover an expired owner', async () => {
    const results = await Promise.all([store.acquireAsset(asset.id, 'one'), store.acquireAsset(asset.id, 'two')]);
    assert.equal(results.filter(Boolean).length, 1);
    const owner = results[0] ? 'one' : 'two';
    await store.releaseAsset(asset.id, 'wrong-owner');
    assert.equal(await store.acquireAsset(asset.id, 'three'), null);
    await store.assets.updateOne({ _id: asset.id }, { $set: { 'collectionLease.until': new Date(0) } });
    assert.ok(await store.acquireAsset(asset.id, 'replacement'));
    await store.releaseAsset(asset.id, owner);
    assert.equal(await store.acquireAsset(asset.id, 'four'), null);
    await store.releaseAsset(asset.id, 'replacement');
    const scans = await Promise.all([store.createScan(asset.id, 'parallel-one'), store.createScan(asset.id, 'parallel-two')]);
    await Promise.all(scans.map(item => until(() => store.getScan(item.id), value => value.status === 'partial')));
    for (const item of scans) assert.equal((await store.scans.findOne({ _id: item.id })).resultWrites, 1);
    assert.equal(maximumActive, 1);
  });
  await t.test('legacy requests keep orchestration semantics and expose empty evidence', async () => {
    await dispatcher.close();
    const legacy = await store.createScan(asset.id, 'legacy-request');
    await store.scans.updateOne({ _id: legacy.id }, { $unset: { executionMode: '' }, $set: { schemaVersion: '1.0.0' } });
    await queue.queue.add('legacy', { scanId: legacy.id }, { jobId: legacy.id });
    await until(() => store.getScan(legacy.id), value => value.status === 'partial');
    assert.deepEqual(await store.getObservations(legacy.id), { scanId: legacy.id, items: [] });
    assert.equal((await request('/api/scans/' + randomUUID() + '/observations')).status, 404);
  });
});
