import assert from 'node:assert/strict';
import { randomUUID, X509Certificate } from 'node:crypto';
import { test } from 'node:test';
import { createCollector, loadTrustProfiles } from '@ai-security/orchestration/collector';
import { createNetworkPolicy, limits } from '@ai-security/orchestration/network-policy';
import { validateContract } from '@ai-security/contracts';
import { certificate } from '../../packages/orchestration/src/collector/tls.js';
import { startCollectorLab } from '../fixtures/tls/collector-harness.mjs';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';

test('product collector measures actual loopback TLS and HTTP fixtures', { timeout: 30000 }, async t => {
  const lab = await startCollectorLab();
  t.after(lab.stop);
  const scan = { id: randomUUID() };
  const asset = { hostname: 'valid.lab.test' };
  const collect = (secure = 'valid', plain = 'no-redirect', overrides = {}) => createCollector({}, {
    policy: lab.policy, trustProfiles: lab.trustProfiles, roots: () => [lab.url(secure), lab.url(plain)],
    bounds: { ...limits, requestMs: 400, scanMs: 3000 }, ...overrides,
  })(scan, asset);
  const tlsResult = result => result.observations.find(item => item.source === 'tls');
  function valid(result) {
    for (const item of result.observations) {
      const checked = validateContract('Observation', item);
      assert.equal(checked.valid, true, JSON.stringify(checked.errors));
    }
  }
  await t.test('SNI, hostname, certificate identity, signatures, keys and protocol are recorded', async () => {
    for (const fixture of ['valid', 'sni', 'ec', 'expiring']) {
      const result = await collect(fixture);
      valid(result);
      const item = tlsResult(result);
      assert.equal(item.status, 'ok', JSON.stringify(item.error));
      assert.equal(item.evidence.authorized, true);
      assert.equal(item.evidence.hostnameMatches, true);
      assert.equal(item.endpoint.ip, '127.0.0.1');
      assert.equal(item.endpoint.sni, asset.hostname);
      assert.equal(item.endpoint.certificateSha256, item.evidence.certificate.sha256);
      const cert = new X509Certificate(Buffer.from(item.evidence.certificate.derBase64, 'base64'));
      assert.equal(cert.fingerprint256.replaceAll(':', '').toLowerCase(), item.endpoint.certificateSha256);
      assert.match(item.evidence.certificate.signatureAlgorithm, /sha256|ecdsa/i);
      assert.ok(item.evidence.certificate.keyBits >= 256);
      assert.equal(item.evidence.supportedProtocols, null);
      assert.equal(item.evidence.enumerationComplete, false);
    }
  });
  await t.test('expired and future certificates remain measurable while HTTPS rejects them', async () => {
    for (const [fixture, code] of [['expired', 'CERT_HAS_EXPIRED'], ['future', 'CERT_NOT_YET_VALID']]) {
      const result = await collect(fixture);
      const item = tlsResult(result);
      assert.equal(item.status, 'ok');
      assert.equal(item.evidence.authorized, false);
      assert.ok(item.evidence.authorizationErrors.includes(code));
      assert.equal(item.evidence.hostnameMatches, true);
      assert.ok(result.observations.some(item => item.error?.code === 'tls_verification_error'));
      valid(result);
    }
  });
  await t.test('hostname and chain verification are independent', async () => {
    const wrong = tlsResult(await collect('wrong-host')).evidence;
    assert.equal(wrong.chainAuthorized, true);
    assert.equal(wrong.hostnameMatches, false);
    assert.ok(wrong.authorizationErrors.includes('ERR_TLS_CERT_ALTNAME_INVALID'));
    assert.equal(tlsResult(await collect('chain-complete')).evidence.authorized, true);
    assert.equal(tlsResult(await collect('chain-missing')).evidence.chainAuthorized, false);
  });
  await t.test('an operator-provided trust profile is bound to its exact hostname', async () => {
    assert.equal(tlsResult(await collect('private')).evidence.authorized, false);
    const filename = join(lab.directory, 'profiles.json');
    writeFileSync(filename, JSON.stringify({ 'valid.lab.test': { name: 'approved-private-lab', caFile: 'private-root.pem' } }));
    const result = await collect('private', 'no-redirect', { trustProfiles: loadTrustProfiles(filename) });
    assert.equal(tlsResult(result).evidence.authorized, true);
    assert.equal(tlsResult(result).evidence.trustProfile, 'approved-private-lab');
    assert.ok(result.observations.find(item => item.source === 'http').evidence.authenticated);
  });
  await t.test('HTTP preserves Host and SNI, follows bounded redirects and authenticates HSTS', async () => {
    const result = await collect('capture', 'redirect');
    valid(result);
    assert.ok(lab.requests.some(req => req.id === 'capture' && req.host === 'valid.lab.test:' + lab.endpoints.capture.port && req.sni === asset.hostname));
    const headers = result.observations.filter(item => item.source === 'http');
    assert.equal(headers[0].evidence.hsts, 'max-age=123');
    assert.equal(headers[0].evidence.authenticated, true);
    assert.equal(headers[1].evidence.statusCode, 301);
    assert.equal(headers[2].evidence.authenticated, true);
    assert.equal(headers[2].evidence.redirectHop, 1);
    assert.equal(headers[2].endpoint.certificateSha256, tlsResult(await collect()).endpoint.certificateSha256);
    const forged = await collect('valid', 'forged-hsts');
    assert.equal(forged.observations.at(-1).evidence.hsts, null);
    for (const fixture of ['hsts-missing', 'hsts-invalid', 'hsts-disabled']) {
      assert.equal((await collect(fixture)).observations[1].status, 'ok');
    }
  });
  await t.test('redirects are checked by public policy before contacting forbidden destinations', async () => {
    for (const fixture of ['blocked-redirect', 'mapped-redirect']) {
      const publicPolicy = createNetworkPolicy('valid.lab.test', async () => ['127.0.0.1']);
      const policy = { prepare: (url, signal) => url.includes('valid.lab.test:') ? lab.policy.prepare(url, signal) : publicPolicy.prepare(url, signal) };
      const result = await collect('valid', fixture, { policy });
      assert.equal(result.observations.at(-1).error.code, 'target_blocked');
    }
    assert.equal((await collect('valid', 'loop')).observations.at(-1).error.code, 'redirect_loop');
    assert.equal((await collect('valid', 'many-redirects')).observations.at(-1).error.code, 'redirect_limit');
  });
  await t.test('body size, header size, slow responses and stalled TLS are bounded collection errors', async () => {
    assert.equal((await collect('valid', 'large-body')).observations.at(-1).error.code, 'response_too_large');
    assert.equal((await collect('valid', 'large-header')).observations.at(-1).status, 'error');
    assert.equal((await collect('valid', 'slow-body')).observations.at(-1).error.code, 'timeout');
    const result = await collect('timeout');
    assert.equal(tlsResult(result).error.code, 'timeout');
    assert.equal(result.status, 'partial');
    assert.equal(result.sources.find(source => source.source === 'tls').status, 'error');
    const deadline = Date.now();
    const bounded = await collect('timeout', 'slow-body', { bounds: { ...limits, requestMs: 1000, scanMs: 100 } });
    assert.ok(Date.now() - deadline < 1500);
    assert.equal(tlsResult(bounded).error.code, 'timeout');
  });
  await t.test('public collection refuses loopback DNS answers before opening a fixture connection', async () => {
    const before = lab.requests.length;
    const result = await createCollector({ allowedTargets: asset.hostname }, {
      policy: createNetworkPolicy(asset.hostname, async () => ['127.0.0.1']),
    })(scan, asset);
    assert.ok(result.observations.every(item => item.error.code === 'target_blocked'));
    assert.equal(lab.requests.length, before);
  });
  await t.test('offline weak-key and SHA-1 certificates preserve their actual metadata', () => {
    assert.equal(certificate(lab.read('weak-key.pem')).keyBits, 1024);
    assert.match(certificate(lab.read('sha1.pem')).signatureAlgorithm, /sha1/i);
  });
});
