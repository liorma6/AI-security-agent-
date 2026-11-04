import { spawnSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { root } from './local-services.mjs';
import { startLab } from '../tests/fixtures/tls/lab.mjs';

const directory = resolve(root, 'tests/fixtures/tls/generated');
mkdirSync(directory, { recursive: true });
const python = resolve(root, 'services/ml/.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const result = spawnSync(python, [resolve(root, 'tests/fixtures/tls/generate.py'), '--out', directory], { stdio: 'inherit', windowsHide: true });
if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);
if (!process.argv.includes('--generate-only')) {
  const lab = await startLab(directory);
  writeFileSync(resolve(directory, 'endpoints.json'), JSON.stringify(lab.endpoints, null, 2) + '\n');
  console.log('Local-only lab endpoints (ephemeral ports):');
  console.table(Object.values(lab.endpoints).map(({ id, protocol, host, port, servername }) => ({ id, protocol, host, port, servername })));
  await new Promise((done) => {
    process.once('SIGINT', done);
    process.once('SIGTERM', done);
  });
  await lab.stop();
}
