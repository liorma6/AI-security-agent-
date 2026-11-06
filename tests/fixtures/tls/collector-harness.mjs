import { mkdirSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { resolve, join } from 'node:path';
import { once } from 'node:events';
import http from 'node:http';
import https from 'node:https';
import { root } from '../../../scripts/local-services.mjs';
import { startLab } from './lab.mjs';
import { CollectionError } from '@ai-security/orchestration/network-policy';

// Test-only policy. Only listeners created by this invocation can be reached.
export async function startCollectorLab() {
  const generated = resolve(root, 'tests/fixtures/tls/generated');
  mkdirSync(generated, { recursive: true });
  const directory = mkdtempSync(join(generated, 'collector-'));
  const python = resolve(root, 'services/ml/.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const result = spawnSync(python, [resolve(root, 'tests/fixtures/tls/generate.py'), '--out', directory], { encoding: 'utf8', windowsHide: true });
  if (result.error || result.status !== 0) throw result.error ?? new Error(result.stderr);
  const read = name => readFileSync(resolve(directory, name));
  const lab = await startLab(directory);
  const servers = [];
  const sockets = new Set();
  const requests = [];
  const url = id => {
    const entry = lab.endpoints[id];
    return (entry.protocol === 'http' ? 'http:' : 'https:') + '//valid.lab.test:' + entry.port + '/';
  };
  async function add(id, handler, secure = false) {
    const handle = (req, res) => {
      requests.push({ id, host: req.headers.host, sni: req.socket.servername, path: req.url });
      handler(req, res);
    };
    const server = secure ? https.createServer({ key: read('valid-key.pem'), cert: read('valid.pem') }, handle) : http.createServer(handle);
    server.on('connection', socket => { sockets.add(socket); socket.on('close', () => sockets.delete(socket)); socket.on('error', () => {}); });
    server.on('tlsClientError', () => {});
    server.listen(0, '127.0.0.1');
    await once(server, 'listening');
    servers.push(server);
    lab.endpoints[id] = { host: '127.0.0.1', port: server.address().port, protocol: secure ? 'https' : 'http', servername: 'valid.lab.test' };
  }
  await add('capture', (_req, res) => { res.setHeader('Strict-Transport-Security', 'max-age=123'); res.end('OK'); }, true);
  await add('forged-hsts', (_req, res) => { res.setHeader('Strict-Transport-Security', 'max-age=999'); res.end('OK'); });
  await add('blocked-redirect', (_req, res) => { res.writeHead(302, { Location: 'http://127.0.0.1:1/' }); res.end(); });
  await add('mapped-redirect', (_req, res) => { res.writeHead(302, { Location: 'http://[::ffff:127.0.0.1]/' }); res.end(); });
  await add('loop', (_req, res) => { res.writeHead(302, { Location: url('loop') }); res.end(); });
  await add('many-redirects', (req, res) => {
    const n = Number(new URL(req.url, 'http://lab.invalid').searchParams.get('n') ?? 0);
    res.writeHead(302, { Location: url('many-redirects') + '?n=' + (n + 1) }); res.end();
  });
  await add('large-body', (_req, res) => res.end('x'.repeat(70000)));
  await add('large-header', (_req, res) => { res.setHeader('X-Lab', 'x'.repeat(20000)); res.end(); });
  await add('slow-body', (_req, res) => {
    res.writeHead(200); res.write('x');
    const timer = setInterval(() => res.write('x'), 20);
    res.on('close', () => clearInterval(timer));
  });
  const policy = {
    async prepare(value, signal) {
      signal?.throwIfAborted();
      const parsed = new URL(value);
      const entry = Object.values(lab.endpoints).find(item => item.port === Number(parsed.port));
      if (!entry || parsed.hostname !== 'valid.lab.test' || parsed.username || parsed.password ||
          parsed.protocol !== (entry.protocol === 'http' ? 'http:' : 'https:')) {
        throw new CollectionError('target_blocked', 'The destination is outside this test laboratory.');
      }
      return { url: parsed.href, hostname: parsed.hostname, address: entry.host, family: 4,
        port: entry.port, protocol: parsed.protocol, path: parsed.pathname + parsed.search, authority: parsed.host };
    },
  };
  async function stop() {
    for (const socket of sockets) socket.destroy();
    await Promise.all(servers.map(server => new Promise(done => server.close(done))));
    await lab.stop();
    // This directory is created by mkdtemp inside the ignored fixture directory.
    rmSync(directory, { recursive: true, force: true });
  }
  return { ...lab, directory, read, url, policy, requests, stop,
    trustProfiles: { 'valid.lab.test': { name: 'disposable-lab-root', ca: read('root.pem') } } };
}
