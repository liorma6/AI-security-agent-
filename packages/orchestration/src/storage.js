import { randomUUID } from 'node:crypto';
import { MongoClient } from 'mongodb';
import { validateContract } from '@ai-security/contracts';
import { RequestError } from './targets.js';

const publicRecord = (record) => {
  if (!record) return null;
  const { _id, requestKey, dispatchAt, executions, resultWrites, collectedObservations, collectionLease, ...value } = record;
  void _id; void requestKey; void dispatchAt; void executions; void resultWrites;
  void collectedObservations; void collectionLease;
  return value;
};
const now = () => new Date().toISOString();

export async function openStore(config) {
  const client = new MongoClient(config.mongoUrl, {
    serverSelectionTimeoutMS: 2000, connectTimeoutMS: 2000, socketTimeoutMS: 5000,
    writeConcern: { w: 'majority', journal: true },
  });
  try {
    await client.connect();
    const db = client.db(config.database);
    const assets = db.collection('assets');
    const scans = db.collection('scans');
    await Promise.all([
      assets.createIndex({ hostname: 1 }, { unique: true }),
      scans.createIndex({ requestKey: 1 }, { unique: true }),
      scans.createIndex({ status: 1, dispatchAt: 1 }),
      scans.createIndex({ assetId: 1, createdAt: -1 }),
    ]);
    return {
      db, assets, scans,
      close: () => client.close(),
      ping: () => db.command({ ping: 1 }),
      async createAsset(hostname) {
        const createdAt = now();
        const id = randomUUID();
        const record = {
          _id: id, id, schemaVersion: '1.2.0', hostname, createdAt,
          authorization: { scope: 'public', approvedBy: 'server-allowlist', approvedAt: createdAt, policyVersion: '1.0.0' },
        };
        // A unique hostname also arbitrates simultaneous requests from several API processes.
        try { await assets.updateOne({ hostname }, { $setOnInsert: record }, { upsert: true }); }
        catch (error) { if (error.code !== 11000) throw error; }
        return publicRecord(await assets.findOne({ hostname }));
      },
      async listAssets({ limit, cursor }) {
        const records = await assets.find(cursor ? { _id: { $gt: cursor } } : {}).sort({ _id: 1 }).limit(limit + 1).toArray();
        const hasMore = records.length > limit;
        const items = records.slice(0, limit);
        return { items: items.map(publicRecord), nextCursor: hasMore ? items.at(-1)._id : null };
      },
      async getAsset(id) { return publicRecord(await assets.findOne({ _id: id })); },
      async createScan(assetId, requestKey) {
        const id = randomUUID();
        const record = {
          _id: id, id, assetId, requestKey, schemaVersion: '1.2.0',
          executionMode: config.mode === 'collection' ? 'collection' : 'orchestration_test', status: 'queued', createdAt: now(),
          startedAt: null, completedAt: null, attempt: 1, executions: 0, resultWrites: 0,
          dispatchAt: new Date(0), policyVersion: '1.0.0',
          sources: ['tls', 'http', 'dns', 'ssllabs'].map(source => ({ source, status: 'pending', reason: null })),
        };
        try { await scans.insertOne(record); }
        catch (error) { if (error.code !== 11000) throw error; }
        const stored = await scans.findOne({ requestKey });
        if (stored.assetId !== assetId) throw new RequestError(409, 'conflict', 'This Idempotency-Key belongs to a different asset.');
        return publicRecord(stored);
      },
      async getScan(id) { return publicRecord(await scans.findOne({ _id: id })); },
      async getObservations(id) {
        const record = await scans.findOne({ _id: id }, { projection: { collectedObservations: 1 } });
        return record ? { scanId: id, items: record.collectedObservations ?? [] } : null;
      },
      async acquireAsset(id, owner) {
        return assets.findOneAndUpdate({
          _id: id, $or: [{ collectionLease: { $exists: false } }, { 'collectionLease.until': { $lte: new Date() } }],
        }, { $set: { collectionLease: { owner, until: new Date(Date.now() + 45000) } } }, { returnDocument: 'after' });
      },
      async releaseAsset(id, owner) {
        await assets.updateOne({ _id: id, 'collectionLease.owner': owner }, { $unset: { collectionLease: '' } });
      },
      async finishCollection(id, result) {
        if (!validateContract('ObservationList', { scanId: id, items: result.observations }).valid ||
            result.observations.some(item => item.scanId !== id) ||
            !result.sources.every(source => validateContract('SourceState', source).valid) ||
            !['completed', 'partial', 'failed'].includes(result.status)) throw new Error('Invalid collected result');
        return scans.updateOne({ _id: id, status: { $in: ['queued', 'running'] } }, {
          $set: { status: result.status, completedAt: now(), sources: result.sources, collectedObservations: result.observations },
          $inc: { resultWrites: 1 },
        });
      },
      async beginScan(id) {
        return scans.findOneAndUpdate(
          { _id: id, status: { $in: ['queued', 'running'] } },
          [{ $set: {
            status: 'running', startedAt: { $ifNull: ['$startedAt', now()] },
            executions: { $add: [{ $ifNull: ['$executions', 0] }, 1] },
            attempt: { $add: [{ $ifNull: ['$executions', 0] }, 1] },
          } }],
          { returnDocument: 'after' },
        );
      },
      async finishScan(id, status, reason) {
        // A single conditional update commits the result and terminal state together.
        return scans.updateOne({ _id: id, status: { $in: ['queued', 'running'] } }, {
          $set: { status, completedAt: now(), sources: ['tls', 'http', 'dns', 'ssllabs'].map(source => ({
            source, status: 'unavailable', reason,
          })) },
          $inc: { resultWrites: 1 },
        });
      },
    };
  } catch (error) {
    await client.close();
    throw error;
  }
}
