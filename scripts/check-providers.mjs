// Read-only availability checks. This script never starts a target assessment.
const checks = [
  {
    provider: 'google-dns',
    url: 'https://dns.google/resolve?name=example.com&type=A',
    validate(data) {
      if (data.Status !== 0 || !Array.isArray(data.Answer)) throw new Error('Unexpected DNS response');
      return { dnsStatus: data.Status, answerCount: data.Answer.length };
    },
  },
  {
    provider: 'ssl-labs',
    url: 'https://api.ssllabs.com/api/v4/info',
    validate(data) {
      if (!data.engineVersion || !Number.isInteger(data.maxAssessments)) throw new Error('Unexpected SSL Labs info');
      return { engineVersion: data.engineVersion, assessmentVerified: false, registrationRequired: true };
    },
  },
];
for (const check of checks) {
  try {
    const response = await fetch(check.url, { signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    console.log(JSON.stringify({ provider: check.provider, available: true, checkedAt: new Date().toISOString(), ...check.validate(await response.json()) }));
  } catch (error) {
    console.error(JSON.stringify({ provider: check.provider, available: false, error: error.message }));
    process.exitCode = 1;
  }
}
