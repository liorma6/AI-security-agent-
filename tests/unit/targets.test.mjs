import assert from 'node:assert/strict';
import { test } from 'node:test';
import { normalizeHostname, targetPolicy } from '@ai-security/orchestration/targets';
import { settings } from '@ai-security/orchestration/settings';

test('hostnames and root URLs normalize to the same allowlist identity', () => {
  for (const input of ['Example.COM', ' example.com. ', 'https://EXAMPLE.com/', 'http://example.com:80/']) {
    assert.equal(normalizeHostname(input), 'example.com');
  }
  assert.equal(normalizeHostname('bücher.example'), 'xn--bcher-kva.example');
});
test('unsafe target syntax is rejected before storage', () => {
  for (const input of [null, '', '127.0.0.1', '[::1]', 'http://2130706433/', 'https://user:pass@example.com/',
    'https://example.com:8080', 'https://example.com/path', 'https://example.com/?q=a', 'https://example.com/#a',
    '*.example.com', 'localhost', 'service.local', 'metadata.internal', 'ftp://example.com', 'a b.example', 'example.com:443',
    'example.com/path', 'example.com?query=1', 'example.com#fragment', 'example.com\\path', 'exam\nple.com', 'example%2ecom']) {
    assert.throws(() => normalizeHostname(input), { status: 400 }, String(input));
  }
});
test('allowlist defaults to deny and authorizes only the exact normalized hostname', () => {
  assert.throws(() => targetPolicy().authorize('example.com'), { status: 403 });
  const policy = targetPolicy('EXAMPLE.com, https://demo.example.com/');
  assert.equal(policy.authorize('example.com'), 'example.com');
  for (const name of ['sub.example.com', 'example.com.attacker.com']) {
    assert.throws(() => policy.authorize(name), { status: 403 });
  }
});
test('invalid configuration fails before a service starts', () => {
  for (const env of [{ APP_MODE: 'production' }, { MONGO_DATABASE: '$bad' }, { QUEUE_NAME: 'bad:name' }, { REDIS_URL: 'https://example.com' }]) {
    assert.throws(() => settings(env));
  }
  assert.equal(settings({}).mode, 'bootstrap');
});
