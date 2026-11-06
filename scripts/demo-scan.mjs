import { randomUUID } from 'node:crypto';
import { setTimeout as delay } from 'node:timers/promises';

const hostname = process.argv[2];
if (!hostname) throw new Error('Supply an allowlisted hostname: npm run demo -- demo.example.com');
const base = 'http://127.0.0.1:' + (process.env.API_PORT ?? 3001);
async function request(path, body) {
  const response = await fetch(base + path, {
    method: body ? 'POST' : 'GET', signal: AbortSignal.timeout(10000),
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': randomUUID() },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(JSON.stringify(data));
  return data;
}
const asset = await request('/api/assets', { hostname });
const scan = await request('/api/scans', { assetId: asset.id });
console.log(JSON.stringify({ accepted: scan.id, mode: scan.executionMode }, null, 2));
const deadline = Date.now() + 60000;
while (Date.now() < deadline) {
  const result = await request('/api/scans/' + scan.id);
  if (['partial', 'completed', 'failed'].includes(result.status)) {
    console.log(JSON.stringify(result, null, 2));
    if (result.executionMode === 'collection') {
      console.log(JSON.stringify(await request('/api/scans/' + scan.id + '/observations'), null, 2));
    }
    process.exit(result.status === 'failed' ? 1 : 0);
  }
  await delay(300);
}
throw new Error('Scan is still pending. Check /ready and worker logs.');
