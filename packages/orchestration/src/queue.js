import { Queue, Worker } from 'bullmq';
import Redis from 'ioredis';
import { setTimeout as delay } from 'node:timers/promises';
import { targetPolicy } from './targets.js';

const report = (event, error) => {
  console.error(JSON.stringify({ event, code: error.code ?? error.name }));
};

export function createQueue(config) {
  const connection = new Redis(config.redisUrl, {
    maxRetriesPerRequest: 1, enableOfflineQueue: false,
    connectTimeout: 1000, commandTimeout: 2000,
  });
  connection.on('error', error => report('redis_unavailable', error));
  const queue = new Queue(config.queueName, { connection });
  queue.on('error', error => report('queue_error', error));
  return {
    queue, connection,
    async ping() { return connection.ping(); },
    async close() { await queue.close(); connection.disconnect(); },
  };
}

export function startDispatcher(store, queue, { intervalMs = 1000, onError = report } = {}) {
  let stopped = false;
  let timer;
  let active = Promise.resolve();
  async function reconcile() {
    // The durable dispatch schedule lives in the same document as the accepted request.
    for (let count = 0; count < 50 && !stopped; count++) {
      const scan = await store.scans.findOneAndUpdate(
        { status: { $in: ['queued', 'running'] }, dispatchAt: { $lte: new Date() } },
        { $set: { dispatchAt: new Date(Date.now() + 5000) } },
        { sort: { dispatchAt: 1 }, returnDocument: 'after' },
      );
      if (!scan) return;
      try {
        const existing = await queue.getJob(scan.id);
        if (existing) {
          if (await existing.getState() === 'failed') {
            await store.finishScan(scan.id, 'failed', 'The worker exhausted its retry or stalled-job limit.');
          }
          continue;
        }
        await queue.add('orchestration_test', { scanId: scan.id }, {
          jobId: scan.id, attempts: 3, backoff: { type: 'exponential', delay: 500 },
          removeOnComplete: { count: 1000 }, removeOnFail: { count: 1000 },
        });
      } catch (error) {
        onError('dispatch_retry', error);
        // MongoDB retains the request. The next scheduled pass retries with the same job ID.
        return;
      }
    }
  }
  function tick() {
    active = reconcile().catch(error => onError('dispatch_error', error)).finally(() => {
      if (!stopped) timer = setTimeout(tick, intervalMs);
    });
  }
  tick();
  return { async close() { stopped = true; clearTimeout(timer); await active; } };
}

export function startWorker(store, config, { delayMs = 0 } = {}) {
  const policy = targetPolicy(config.allowedTargets);
  const connection = new Redis(config.redisUrl, { maxRetriesPerRequest: null, connectTimeout: 1000 });
  connection.on('error', error => report('worker_redis_unavailable', error));
  const worker = new Worker(config.queueName, async (job) => {
    const record = await store.getScan(job.data.scanId);
    if (!record || !['queued', 'running'].includes(record.status)) return;
    const started = await store.beginScan(record.id);
    if (!started) return;
    const asset = await store.getAsset(record.assetId);
    try {
      if (!asset) throw new Error('Asset missing');
      policy.authorize(asset.hostname);
    } catch {
      await store.finishScan(record.id, 'failed', 'The target is no longer authorized by server policy.');
      return;
    }
    if (delayMs) await delay(delayMs);
    // Stage 3 proves the queue/storage path. Each security source remains explicitly unmeasured.
    await store.finishScan(record.id, 'partial', 'Orchestration test only. Evidence collection is scheduled for a later stage.');
  }, { connection, concurrency: 2, lockDuration: 10000, stalledInterval: 2000, maxStalledCount: 2 });
  worker.on('error', error => report('worker_error', error));
  worker.on('failed', (_job, error) => report('job_failed', error));
  return {
    worker, connection,
    async close() { await worker.close(); connection.disconnect(); },
  };
}
