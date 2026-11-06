import http from 'node:http';
import https from 'node:https';
import { X509Certificate } from 'node:crypto';
import { verifyHostname } from './tls.js';
import { CollectionError, limits } from './policy.js';

export function collectHttp(target, trust, signal, bounds = limits) {
  return new Promise((resolve, reject) => {
    const secure = target.protocol === 'https:';
    const transport = secure ? https : http;
    const request = transport.request({
      hostname: target.address, port: target.port, family: target.family, autoSelectFamily: false,
      path: target.path, method: 'GET', agent: false, signal,
      servername: target.hostname, ca: trust.ca, rejectUnauthorized: true,
      checkServerIdentity: (_hostname, peer) => verifyHostname(target.hostname, peer),
      minVersion: 'TLSv1.2', ALPNProtocols: ['http/1.1'],
      maxHeaderSize: bounds.maxHeaderBytes,
      headers: { Host: target.authority, 'User-Agent': 'AI-Security-Agent/0.1', Accept: '*/*', 'Accept-Encoding': 'identity', Connection: 'close' },
    }, response => {
      let bytes = 0;
      const raw = secure ? response.socket.getPeerCertificate().raw : null;
      const fingerprint = raw ? new X509Certificate(raw).fingerprint256.replaceAll(':', '').toLowerCase() : null;
      response.on('data', chunk => {
        bytes += chunk.length;
        if (bytes > bounds.maxBodyBytes) request.destroy(new CollectionError('response_too_large', 'HTTP body exceeded the collection limit.'));
      });
      response.once('error', reject);
      response.once('end', () => {
        const location = response.headers.location || null;
        const hsts = secure ? response.headers['strict-transport-security'] || null : null;
        if ([location, hsts].some(value => value !== null && (typeof value !== 'string' || value.length > 2048))) {
          reject(new CollectionError('response_too_large', 'An evidence header exceeded the collection limit.'));
          return;
        }
        resolve({ fingerprint, evidence: { statusCode: response.statusCode, location, hsts,
          url: target.url, authenticated: secure, bodyBytes: bytes } });
      });
    });
    const timer = setTimeout(() => request.destroy(new CollectionError('timeout', 'HTTP request exceeded its time limit.')), bounds.requestMs);
    request.once('close', () => clearTimeout(timer));
    request.once('error', reject);
    request.end();
  });
}
