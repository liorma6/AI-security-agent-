import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { createServer } from 'node:net';
import { once } from 'node:events';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const root = fileURLToPath(new URL('../', import.meta.url));

export function localPorts(env = process.env) {
  const names = { api: ['API_PORT', 3001], scanner: ['SCANNER_PORT', 3002], ml: ['ML_PORT', 8000], web: ['WEB_PORT', 5173] };
  return Object.fromEntries(Object.entries(names).map(([service, [name, fallback]]) => {
    const port = Number(env[name] ?? fallback);
    if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Invalid ' + name);
    return [service, port];
  }));
}

async function assertPortFree(port) {
  const server = createServer();
  server.listen(port, '127.0.0.1');
  await once(server, 'listening');
  await new Promise((resolve) => server.close(resolve));
}

export async function startServices({ preview = false, stdio = 'inherit', ports = localPorts() } = {}) {
  if (new Set(Object.values(ports)).size !== 4) throw new Error('Service ports must be distinct');
  await Promise.all(Object.values(ports).map(assertPortFree));
  const mlRoot = resolve(root, 'services/ml');
  const python = resolve(mlRoot, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  if (!existsSync(python)) throw new Error('Run uv sync --project services/ml --frozen first');
  const vite = resolve(root, 'node_modules/vite/bin/vite.js');
  const definitions = [
    { name: 'api', command: process.execPath, args: ['services/api/src/index.js'], port: ports.api },
    { name: 'scanner', command: process.execPath, args: ['services/scanner/src/index.js'], port: ports.scanner },
    { name: 'ml', command: python, args: ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(ports.ml)], cwd: mlRoot },
    { name: 'web', command: process.execPath, args: [vite, ...(preview ? ['preview'] : []), 'apps/web', '--host', '127.0.0.1', '--port', String(ports.web)] },
  ];
  let stopping = false;
  let resolveFailure;
  const failed = new Promise((resolve) => { resolveFailure = resolve; });
  const children = definitions.map((service) => {
    const child = spawn(service.command, service.args, {
      cwd: service.cwd ?? root,
      env: { ...process.env, HOST: '127.0.0.1', PORT: String(service.port ?? ''), API_TARGET: 'http://127.0.0.1:' + ports.api },
      stdio,
      windowsHide: true,
    });
    child.on('error', (error) => resolveFailure(new Error(service.name + ': ' + error.message)));
    child.on('exit', (code) => {
      if (!stopping) resolveFailure(new Error(service.name + ' exited unexpectedly: ' + code));
    });
    return child;
  });
  async function stop() {
    stopping = true;
    await Promise.all(children.map((child) => new Promise((resolve) => {
      if (child.exitCode !== null || child.signalCode !== null || !child.pid) return resolve();
      const timer = setTimeout(() => { child.kill('SIGKILL'); resolve(); }, 5000);
      child.once('exit', () => { clearTimeout(timer); resolve(); });
      child.kill('SIGTERM');
    })));
  }
  return { stop, ports, failed };
}
