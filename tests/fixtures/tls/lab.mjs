import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import http from 'node:http';
import https from 'node:https';
import net from 'node:net';
import tls from 'node:tls';
import { once } from 'node:events';

// This module is test-only. It never accepts arbitrary targets or binds to non-loopback IPs.
export async function startLab(certDirectory) {
  const material = (file) => readFileSync(resolve(certDirectory, file));
  const servers = [];
  const sockets = new Set();
  const endpoints = {};
  async function add(id, server, protocol, extra = {}) {
    servers.push(server);
    server.on('connection', (socket) => {
      sockets.add(socket);
      socket.on('close', () => sockets.delete(socket));
      socket.on('error', () => {});
    });
    server.on('tlsClientError', () => {});
    server.listen(0, '127.0.0.1');
    await once(server, 'listening');
    endpoints[id] = { id, host: '127.0.0.1', port: server.address().port, servername: 'valid.lab.test', protocol, ...extra };
  }
  const options = (fixture = 'valid', cert = fixture + '.pem') => ({
    key: material(fixture + '-key.pem'), cert: material(cert), minVersion: 'TLSv1.2',
  });
  const respond = (hsts = 'max-age=31536000; includeSubDomains') => (_req, res) => {
    if (hsts !== null) res.setHeader('Strict-Transport-Security', hsts);
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('Local TLS laboratory\n');
  };
  async function stop() {
    for (const socket of sockets) socket.destroy();
    await Promise.all(servers.map((server) => new Promise((resolve) => server.close(resolve))));
  }
  try {
    for (const fixture of ['valid', 'expired', 'future', 'expiring', 'wrong-host', 'private', 'ec']) {
      await add(fixture, https.createServer(options(fixture), respond()), 'https');
    }
    await add('chain-complete', https.createServer(options('chain', 'chain-full.pem'), respond()), 'https');
    await add('chain-missing', https.createServer(options('chain'), respond()), 'https');
    await add('hsts-missing', https.createServer(options(), respond(null)), 'https');
    await add('hsts-invalid', https.createServer(options(), respond('max-age=invalid')), 'https');
    await add('hsts-disabled', https.createServer(options(), respond('max-age=0')), 'https');
    const validContext = tls.createSecureContext(options());
    const wrongContext = tls.createSecureContext(options('wrong-host'));
    await add('sni', https.createServer({
      ...options('wrong-host'),
      SNICallback: (name, callback) => callback(null, name === 'valid.lab.test' ? validContext : wrongContext),
    }, respond()), 'https');
    await add('modern-protocol', https.createServer({
      ...options(), minVersion: 'TLSv1.2', maxVersion: 'TLSv1.2',
    }, respond()), 'https');
    // Deliberately weak settings are confined to this single loopback test server.
    await add('legacy-protocol', https.createServer({
      ...options(), minVersion: 'TLSv1', maxVersion: 'TLSv1', ciphers: 'DEFAULT:@SECLEVEL=0',
    }, respond()), 'https');
    await add('redirect', http.createServer((_req, res) => {
      res.writeHead(301, { Location: 'https://valid.lab.test:' + endpoints.valid.port + '/' });
      res.end();
    }), 'http');
    await add('no-redirect', http.createServer(respond(null)), 'http');
    await add('timeout', net.createServer(() => {}), 'tcp');
    return { endpoints, stop };
  } catch (error) {
    await stop();
    throw error;
  }
}
