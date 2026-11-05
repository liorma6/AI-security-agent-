import { randomUUID } from 'node:crypto';
import { MongoClient } from 'mongodb';
import { RequestError } from './targets.js';

const publicRecord = (record) => {
  if (!record) return null;
  const { _id, requestKey, dispatchAt, executions, resultWrites, ...value } = record;
  void _id; void requestKey; void dispatchAt; void executions; void resultWrites;
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
          _id: id, id, schemaVersion: '1.1.0', hostname, createdAt,
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
          _id: id, id, assetId, requestKey, schemaVersion: '1.1.0',
          executionMode: 'orchestration_test', status: 'queued', createdAt: now(),
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
