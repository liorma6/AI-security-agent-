import { randomUUID } from 'node:crypto';
import express from 'express';
import { createServiceApp } from '@ai-security/runtime';
import { validateContract } from '@ai-security/contracts';
import { normalizeHostname, RequestError, targetPolicy } from '@ai-security/orchestration/targets';

function requireValid(schema, value) {
  if (!validateContract(schema, value).valid) throw new RequestError(400, 'invalid_request', 'Request does not match ' + schema + '.');
}
function uuid(value) {
  if (typeof value !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)) {
    throw new RequestError(400, 'invalid_request', 'A UUID is required.');
  }
  return value.toLowerCase();
}
function pagination(query) {
  if (Object.keys(query).some(key => !['limit', 'cursor'].includes(key))) throw new RequestError(400, 'invalid_request', 'Unknown query parameter.');
  const limit = query.limit === undefined ? 25 : Number(query.limit);
  if ((query.limit !== undefined && (typeof query.limit !== 'string' || !/^\d+$/.test(query.limit))) ||
      !Number.isInteger(limit) || limit < 1 || limit > 100) throw new RequestError(400, 'invalid_request', 'Limit must be between 1 and 100.');
  return { limit, cursor: query.cursor === undefined ? null : uuid(query.cursor) };
}

export function createApp({ store, queue, allowedTargets = '', mode = 'orchestration_test' } = {}) {
  const enabled = Boolean(store);
  const policy = targetPolicy(allowedTargets);
  return createServiceApp({
    service: 'api', healthPaths: ['/health', '/api/health'],
    stage: enabled ? (mode === 'collection' ? 4 : 3) : 1, mode: enabled ? mode : 'bootstrap',
    capabilities: { scanning: enabled && mode === 'collection', persistence: enabled, ...(enabled ? { scanRequests: true } : {}) },
    configure(app) {
      app.get('/ready', async (_req, res) => {
        if (!enabled) return res.status(503).json({ status: 'degraded', dependencies: { mongo: false, redis: false } });
        const results = await Promise.allSettled([store.ping(), queue.ping()]);
        const dependencies = { mongo: results[0].status === 'fulfilled', redis: results[1].status === 'fulfilled' };
        const ready = dependencies.mongo && dependencies.redis;
        res.set('Cache-Control', 'no-store').status(ready ? 200 : 503).json({ status: ready ? 'ready' : 'degraded', dependencies });
      });
      if (!enabled) {
        const unavailable = (_req, res) => res.status(503).json({ error: {
          code: 'service_unavailable', message: 'Enable collection or orchestration_test mode with MongoDB and Redis.',
        } });
        app.post('/api/assets', unavailable);
        app.get('/api/assets', unavailable);
        app.post('/api/scans', unavailable);
        app.get('/api/scans/:scanId', unavailable);
        app.get('/api/scans/:scanId/observations', unavailable);
        return;
      }
      app.use('/api', express.json({ limit: '16kb' }));
      app.use('/api', (_req, res, next) => { res.set('Cache-Control', 'no-store'); next(); });
      app.post('/api/assets', async (req, res) => {
        const input = { ...req.body, hostname: normalizeHostname(req.body?.hostname) };
        requireValid('CreateAssetRequest', input);
        policy.authorize(input.hostname);
        const asset = await store.createAsset(input.hostname);
        res.status(201).json(asset);
      });
      app.get('/api/assets', async (req, res) => res.json(await store.listAssets(pagination(req.query))));
      app.post('/api/scans', async (req, res) => {
        requireValid('CreateScanRequest', req.body);
        const asset = await store.getAsset(uuid(req.body.assetId));
        if (!asset) throw new RequestError(404, 'not_found', 'Asset not found.');
        policy.authorize(asset.hostname);
        const key = req.get('Idempotency-Key') ?? randomUUID();
        if (!/^[a-zA-Z0-9_-]{1,128}$/.test(key)) throw new RequestError(400, 'invalid_request', 'Invalid Idempotency-Key.');
        const scan = await store.createScan(asset.id, key);
        res.set('Location', '/api/scans/' + scan.id).status(202).json(scan);
      });
      app.get('/api/scans/:scanId', async (req, res) => {
        const scan = await store.getScan(uuid(req.params.scanId));
        if (!scan) throw new RequestError(404, 'not_found', 'Scan not found.');
        res.json(scan);
      });
      app.get('/api/scans/:scanId/observations', async (req, res) => {
        const result = await store.getObservations(uuid(req.params.scanId));
        if (!result) throw new RequestError(404, 'not_found', 'Scan not found.');
        res.json(result);
      });
      app.use((error, _req, res, _next) => {
        void _next;
        let status = error.status ?? 503;
        let code = error.code ?? 'service_unavailable';
        let message = error instanceof RequestError ? error.message : 'Storage is temporarily unavailable. Retry with the same Idempotency-Key.';
        if (error.type === 'entity.parse.failed' || error.type === 'entity.too.large') {
          status = error.type === 'entity.too.large' ? 413 : 400;
          code = 'invalid_request'; message = 'Supply a JSON body up to 16 KB.';
        }
        if (!(error instanceof RequestError) && !error.type) {
          status = 503; code = 'service_unavailable';
        }
        res.status(status).json({ error: { code, message } });
      });
    },
  });
}
