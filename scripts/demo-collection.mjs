import { randomUUID } from 'node:crypto';
import { createCollector } from '@ai-security/orchestration/collector';
import { startCollectorLab } from '../tests/fixtures/tls/collector-harness.mjs';

const lab = await startCollectorLab();
try {
  const collect = createCollector({}, {
    policy: lab.policy, trustProfiles: lab.trustProfiles,
    roots: () => [lab.url('expired'), lab.url('redirect')],
  });
  const result = await collect({ id: randomUUID() }, { hostname: 'valid.lab.test' });
  const tls = result.observations.find(item => item.source === 'tls');
  if (tls.status !== 'ok' || !tls.evidence.authorizationErrors.includes('CERT_HAS_EXPIRED')) {
    throw new Error('The collector did not measure the known expired fixture.');
  }
  console.log(JSON.stringify({
    environment: 'disposable loopback laboratory', status: result.status,
    certificate: { subject: tls.evidence.certificate.subject, notAfter: tls.evidence.certificate.notAfter,
      fingerprint: tls.evidence.certificate.sha256 },
    verificationErrors: tls.evidence.authorizationErrors,
    observations: result.observations.map(item => ({
      source: item.source, endpoint: item.endpoint, status: item.status,
      http: item.source === 'http' ? item.evidence : undefined, error: item.error,
    })),
  }, null, 2));
} finally { await lab.stop(); }
