import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createNetworkPolicy, publicAddress, CollectionError } from '@ai-security/orchestration/network-policy';

test('public address policy covers IPv4, IPv6, mapped forms and special-use ranges', () => {
  for (const address of ['127.0.0.1', '10.1.2.3', '172.16.0.1', '192.168.1.1', '169.254.169.254',
    '0.0.0.0', '100.64.0.1', '198.18.0.1', '192.0.2.1', '198.51.100.1', '203.0.113.1',
    '224.0.0.1', '240.0.0.1', '::', '::1', 'fc00::1', 'fe80::1', 'fe80::1%eth0', 'ff02::1',
    '2001:db8::1', '2002:7f00:1::', '64:ff9b::7f00:1', '::ffff:127.0.0.1', '::ffff:7f00:1',
    '::ffff:192.168.1.1', '2130706433', '127.1', 'garbage']) assert.equal(publicAddress(address), false, address);
  for (const address of ['8.8.8.8', '1.1.1.1', '2606:4700:4700::1111', '2001:4860:4860::8888']) assert.equal(publicAddress(address), true, address);
});

test('policy checks every DNS answer before choosing a pinned connection address', async () => {
  for (const answers of [['8.8.8.8', '127.0.0.1'], ['8.8.8.8', '::ffff:169.254.169.254'],
    ['8.8.8.8', '2001:db8::1'], [], Array(17).fill('8.8.8.8')]) {
    const policy = createNetworkPolicy('allowed.example', async () => answers);
    await assert.rejects(policy.prepare('https://allowed.example/'), { code: 'target_blocked' });
  }
});

test('each redirect preparation resolves again and rejects a rebinding answer', async () => {
  let queries = 0;
  const policy = createNetworkPolicy('allowed.example', async () => ++queries === 1 ? ['8.8.8.8'] : ['127.0.0.1']);
  const first = await policy.prepare('https://allowed.example/');
  assert.equal(first.address, '8.8.8.8');
  assert.equal(first.hostname, 'allowed.example');
  assert.equal(first.authority, 'allowed.example');
  await assert.rejects(policy.prepare('https://allowed.example/next'), { code: 'target_blocked' });
  assert.equal(first.address, '8.8.8.8');
  assert.equal(queries, 2);
});

test('forbidden redirect schemes, authorities and ports fail before DNS', async () => {
  let queries = 0;
  const policy = createNetworkPolicy('allowed.example', async () => { queries++; return ['8.8.8.8']; });
  for (const url of ['file:///secret', 'ftp://allowed.example/', 'http://127.0.0.1/',
    'http://[::ffff:127.0.0.1]/', 'https://allowed.example:8080/', 'https://user:pass@allowed.example/',
    'https://other.example/', 'https://allowed.example.attacker.example/']) {
    await assert.rejects(policy.prepare(url), { code: 'target_blocked' }, url);
  }
  assert.equal(queries, 0);
});

test('a DNS failure prevents a target from being selected', async () => {
  const policy = createNetworkPolicy('allowed.example', async () => { throw new CollectionError('dns_error', 'Synthetic DNS failure'); });
  await assert.rejects(policy.prepare('https://allowed.example/'), { code: 'dns_error' });
});
