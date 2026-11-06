import { randomUUID, X509Certificate } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { rootCertificates } from 'node:tls';
import { validateContract } from '@ai-security/contracts';
import { normalizeHostname } from '../targets.js';
import { createNetworkPolicy, CollectionError, errorDetails, limits } from './policy.js';
import { collectTls } from './tls.js';
import { collectHttp } from './http.js';

export function loadTrustProfiles(filename) {
  if (!filename) return {};
  const document = JSON.parse(readFileSync(filename, 'utf8'));
  if (!document || typeof document !== 'object' || Array.isArray(document)) throw new Error('Invalid trust profile file');
  const profiles = {};
  for (const [hostname, profile] of Object.entries(document)) {
    if (normalizeHostname(hostname) !== hostname || !profile || typeof profile.name !== 'string' ||
        profile.name.length < 1 || profile.name.length > 100 || typeof profile.caFile !== 'string') {
      throw new Error('Invalid target trust profile');
    }
    const ca = readFileSync(resolve(dirname(filename), profile.caFile), 'utf8');
    if (ca.length > limits.maxCertificateBytes || !new X509Certificate(ca).ca) throw new Error('Invalid custom CA certificate');
    profiles[hostname] = { name: profile.name, ca };
  }
  return profiles;
}

function endpoint(url, target, fingerprint = null) {
  const parsed = new URL(url);
  return { hostname: parsed.hostname, ip: target?.address ?? null,
    port: target?.port ?? Number(parsed.port || (parsed.protocol === 'https:' ? 443 : 80)),
    sni: parsed.protocol === 'https:' ? parsed.hostname : null, certificateSha256: fingerprint };
}

export function createCollector(config, {
  policy = createNetworkPolicy(config.allowedTargets), trustProfiles = loadTrustProfiles(config.trustProfilesFile),
  bounds = limits, roots = hostname => ['https://' + hostname + '/', 'http://' + hostname + '/'],
} = {}) {
  const defaultTrust = { name: 'node-' + process.versions.node + '-bundled-roots', ca: rootCertificates };
  return async function collect(scan, asset) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), bounds.scanMs);
    const observations = [];
    const trustFor = hostname => trustProfiles[hostname] ?? defaultTrust;
    function record(source, url, target, evidence, error = null, fingerprint = null) {
      const observation = { schemaVersion: '1.2.0', id: randomUUID(), scanId: scan.id, source,
        endpoint: endpoint(url, target, fingerprint), observedAt: new Date().toISOString(), fetchedAt: new Date().toISOString(),
        status: error ? 'error' : 'ok', evidence: error ? null : evidence, error: error ? errorDetails(error) : null };
      const checked = validateContract('Observation', observation);
      if (!checked.valid) throw new Error('Collector produced an invalid observation: ' + JSON.stringify(checked.errors));
      observations.push(observation);
    }
    async function httpChain(initial, initialTarget) {
      const visited = new Set();
      let url = initial;
      let target = initialTarget;
      let lastUrl = initial;
      let lastTarget;
      for (let hop = 0; hop <= bounds.maxRedirects; hop++) {
        try {
          controller.signal.throwIfAborted();
          if (visited.has(url)) throw new CollectionError('redirect_loop', 'A redirect repeated a visited URL.');
          visited.add(url);
          target ??= await policy.prepare(url, controller.signal);
          lastUrl = target.url;
          lastTarget = target;
          const result = await collectHttp(target, trustFor(target.hostname), controller.signal, bounds);
          record('http', url, target, { ...result.evidence, redirectHop: hop }, null, result.fingerprint);
          if (![301, 302, 303, 307, 308].includes(result.evidence.statusCode) || !result.evidence.location) return;
          if (hop === bounds.maxRedirects) throw new CollectionError('redirect_limit', 'The redirect limit was reached.');
          const next = new URL(result.evidence.location, url);
          // Fragments never leave the client. Credentials and every destination are checked by policy.
          next.hash = '';
          url = next.href;
          target = undefined;
        } catch (error) {
          // The rejected destination may be an IP literal or another scheme. Keep the last authorized endpoint.
          record('http', lastUrl, lastTarget, null, error);
          return;
        }
      }
    }
    try {
      const [httpsUrl, httpUrl] = roots(asset.hostname);
      let target;
      try {
        target = await policy.prepare(httpsUrl, controller.signal);
        const evidence = await collectTls(target, trustFor(target.hostname), controller.signal, bounds);
        record('tls', httpsUrl, target, evidence, null, evidence.certificate.sha256);
      } catch (error) { record('tls', httpsUrl, target, null, error); }
      await httpChain(httpsUrl, target);
      await httpChain(httpUrl);
      const sources = ['tls', 'http'].map(source => {
        const items = observations.filter(item => item.source === source);
        const failed = items.some(item => item.status !== 'ok');
        return { source, status: failed ? 'error' : 'ok', reason: failed ? 'See the source observations for collection errors.' : null };
      });
      sources.push(...['dns', 'ssllabs'].map(source => ({ source, status: 'unavailable', reason: 'External evidence adapter is scheduled for stage 6.' })));
      return { status: 'partial', sources, observations };
    } finally { clearTimeout(timer); }
  };
}
