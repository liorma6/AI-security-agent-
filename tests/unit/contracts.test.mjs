import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { validateContract } from '@ai-security/contracts';

const valid = JSON.parse(readFileSync(new URL('../../packages/contracts/examples/valid.json', import.meta.url)));
const invalid = JSON.parse(readFileSync(new URL('../../packages/contracts/examples/invalid.json', import.meta.url)));
for (const [name, example] of Object.entries(valid)) {
  test('contract accepts ' + name, () => {
    const result = validateContract(name, example);
    assert.equal(result.valid, true, JSON.stringify(result.errors));
  });
}
for (const example of invalid) {
  test('contract rejects: ' + example.name, () => {
    assert.equal(validateContract(example.schema, example.value).valid, false);
  });
}
test('validation does not coerce or delete submitted fields', () => {
  const input = { hostname: 'example.com', authorization: 'self-approved' };
  const before = structuredClone(input);
  assert.equal(validateContract('CreateAssetRequest', input).valid, false);
  assert.deepEqual(input, before);
});
test('schema names must be explicitly registered', () => {
  assert.throws(() => validateContract('Typo', {}), /Unknown contract/);
});
