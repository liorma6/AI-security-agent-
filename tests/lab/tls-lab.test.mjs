import assert from 'node:assert/strict';
import { test } from 'node:test';
import { spawnSync } from 'node:child_process';
import { X509Certificate } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import tls from 'node:tls';
import https from 'node:https';
import http from 'node:http';
import { root } from '../../scripts/local-services.mjs';
import { startLab } from '../fixtures/tls/lab.mjs';

const directory = resolve(root, 'tests/fixtures/tls/generated');
const python = resolve(root, 'services/ml/.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const generated = spawnSync(python, [resolve(root, 'tests/fixtures/tls/generate.py'), '--out', directory], { encoding: 'utf8', windowsHide: true });
assert.ifError(generated.error);
assert.equal(generated.status, 0, generated.stderr);
const rootCa = readFileSync(resolve(directory, 'root.pem'));
const privateCa = readFileSync(resolve(directory, 'private-root.pem'));
const cert = (id) => new X509Certificate(readFileSync(resolve(directory, id + '.pem')));

function handshake(endpoint, extra = {}) {
  return new Promise((resolve, reject) => {
    const socket = tls.connect({ host: '127.0.0.1', port: endpoint.port, servername: endpoint.servername, ca: rootCa, ...extra });
    socket.setTimeout(1000, () => socket.destroy(Object.assign(new Error('Lab handshake timed out'), { code: 'LAB_TIMEOUT' })));
    socket.once('error', reject);
    socket.once('secureConnect', () => {
      const result = { authorized: socket.authorized, error: socket.authorizationError, peer: socket.getPeerCertificate(), protocol: socket.getProtocol() };
      socket.end();
      resolve(result);
    });
  });
}
function get(endpoint) {
  return new Promise((resolve, reject) => {
    const transport = endpoint.protocol === 'https' ? https : http;
    const req = transport.get({ host: '127.0.0.1', port: endpoint.port, servername: endpoint.servername, ca: rootCa, headers: { Host: endpoint.servername }, agent: false }, (res) => {
      res.resume();
      res.once('end', () => resolve({ status: res.statusCode, headers: res.headers }));
    });
    req.setTimeout(1000, () => req.destroy(new Error('Lab HTTP timeout')));
    req.once('error', reject);
  });
}

test('TLS laboratory proves the properties of generated fixtures', async (t) => {
  const lab = await startLab(directory);
  t.after(lab.stop);
  const ep = lab.endpoints;
  await t.test('all listeners bind only to loopback with distinct ephemeral ports', () => {
    assert.ok(Object.values(ep).every((e) => e.host === '127.0.0.1'));
    assert.equal(new Set(Object.values(ep).map((e) => e.port)).size, Object.keys(ep).length);
  });
  await t.test('valid RSA and EC certificates verify against the lab trust root', async () => {
    assert.equal((await handshake(ep.valid)).authorized, true);
    assert.equal((await handshake(ep.ec)).authorized, true);
  });
  await t.test('expired and future certificates fail verification for the intended reason', async () => {
    await assert.rejects(handshake(ep.expired), { code: 'CERT_HAS_EXPIRED' });
    await assert.rejects(handshake(ep.future), { code: 'CERT_NOT_YET_VALID' });
  });
  await t.test('expiry fixtures remain relative to generation time', () => {
    const manifest = JSON.parse(readFileSync(resolve(directory, 'manifest.json')));
    const now = Date.parse(manifest.generatedAt);
    assert.equal((cert('expiring').validToDate.getTime() - now) / 86400000, 7);
    assert.equal((cert('valid').validToDate.getTime() - now) / 86400000, 90);
    assert.ok(cert('expired').validToDate.getTime() < now);
    assert.ok(cert('future').validFromDate.getTime() > now);
  });
  await t.test('hostname mismatch fails while explicit SNI selects the correct certificate', async () => {
    await assert.rejects(handshake(ep['wrong-host']), { code: 'ERR_TLS_CERT_ALTNAME_INVALID' });
    const withSni = await handshake(ep.sni);
    assert.equal(withSni.authorized, true);
    assert.equal(withSni.peer.fingerprint256.replaceAll(':', '').toLowerCase(), cert('valid').fingerprint256.replaceAll(':', '').toLowerCase());
    const withoutSni = await handshake(ep.sni, { servername: '', rejectUnauthorized: false });
    assert.notEqual(withoutSni.peer.fingerprint256, withSni.peer.fingerprint256);
    assert.ok(tls.checkServerIdentity('valid.lab.test', withoutSni.peer));
  });
  await t.test('a complete chain verifies; omitting the intermediate does not', async () => {
    assert.equal((await handshake(ep['chain-complete'])).authorized, true);
    await assert.rejects(handshake(ep['chain-missing']), (error) => /UNABLE_TO_VERIFY_LEAF_SIGNATURE|UNABLE_TO_GET_ISSUER_CERT/.test(error.code));
  });
  await t.test('private CA trust is explicit, never added to the operating system', async () => {
    await assert.rejects(handshake(ep.private), (error) => /UNABLE_TO_VERIFY_LEAF_SIGNATURE|UNABLE_TO_GET_ISSUER_CERT/.test(error.code));
    assert.equal((await handshake(ep.private, { ca: privateCa })).authorized, true);
  });
  await t.test('strong and weak public keys are available for offline rule tests', () => {
    assert.equal(cert('valid').publicKey.asymmetricKeyDetails.modulusLength, 2048);
    assert.equal(cert('weak-key').publicKey.asymmetricKeyDetails.modulusLength, 1024);
    assert.equal(cert('ec').publicKey.asymmetricKeyType, 'ec');
  });
  await t.test('the obsolete SHA-1 fixture is cryptographically distinct from SHA-256', () => {
    const manifest = JSON.parse(readFileSync(resolve(directory, 'manifest.json')));
    assert.equal(manifest.certificates.sha1.signature, 'sha1');
    assert.notEqual(cert('sha1').fingerprint256, cert('valid').fingerprint256);
    assert.equal(cert('sha1').verify(cert('root').publicKey), true);
  });
  await t.test('modern defaults reject TLS 1.0; the isolated lab probe confirms legacy support', async () => {
    assert.equal((await handshake(ep['modern-protocol'])).protocol, 'TLSv1.2');
    for (const version of ['TLSv1', 'TLSv1.1']) {
      await assert.rejects(handshake(ep['modern-protocol'], { minVersion: version, maxVersion: version, ciphers: 'DEFAULT:@SECLEVEL=0' }), (error) => /PROTOCOL_VERSION|UNSUPPORTED_PROTOCOL/.test(error.code));
    }
    await assert.rejects(handshake(ep['legacy-protocol']));
    const legacy = await handshake(ep['legacy-protocol'], { minVersion: 'TLSv1', maxVersion: 'TLSv1', ciphers: 'DEFAULT:@SECLEVEL=0' });
    assert.equal(legacy.protocol, 'TLSv1');
  });
  await t.test('HTTP redirects and HSTS are measured from real local responses', async () => {
    assert.equal((await get(ep.redirect)).status, 301);
    assert.equal((await get(ep.redirect)).headers.location, 'https://valid.lab.test:' + ep.valid.port + '/');
    assert.equal((await get(ep['no-redirect'])).status, 200);
    assert.equal((await get(ep.valid)).headers['strict-transport-security'], 'max-age=31536000; includeSubDomains');
    assert.equal((await get(ep['hsts-missing'])).headers['strict-transport-security'], undefined);
    assert.equal((await get(ep['hsts-invalid'])).headers['strict-transport-security'], 'max-age=invalid');
    assert.equal((await get(ep['hsts-disabled'])).headers['strict-transport-security'], 'max-age=0');
  });
  await t.test('a stalled handshake is a collection failure rather than an invalid certificate', async () => {
    await assert.rejects(handshake(ep.timeout), { code: 'LAB_TIMEOUT' });
  });
});
