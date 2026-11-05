import { createServiceApp } from '@ai-security/runtime';

export function createApp({ store, queue, worker } = {}) {
  const enabled = Boolean(store);
  return createServiceApp({
    service: 'scanner', stage: enabled ? 3 : 1,
    mode: enabled ? 'orchestration_test' : 'bootstrap',
    capabilities: { scanning: false, queueConsumer: enabled },
    configure(app) {
      app.get('/ready', async (_req, res) => {
        if (!enabled) return res.status(503).json({ status: 'degraded', dependencies: { mongo: false, redis: false } });
        const results = await Promise.allSettled([store.ping(), queue.ping()]);
        const dependencies = { mongo: results[0].status === 'fulfilled', redis: results[1].status === 'fulfilled' && worker.worker.isRunning() };
        const ready = dependencies.mongo && dependencies.redis;
        res.set('Cache-Control', 'no-store').status(ready ? 200 : 503).json({ status: ready ? 'ready' : 'degraded', dependencies });
      });
    },
  });
}
