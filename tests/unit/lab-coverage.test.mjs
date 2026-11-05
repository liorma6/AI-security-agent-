import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { schema, validateContract } from '@ai-security/contracts';

const read = (path) => JSON.parse(readFileSync(new URL(path, import.meta.url)));
const catalog = read('../../packages/contracts/policy/rules.json');
const fixtures = read('../fixtures/tls/cases.json').fixtures;
const fixtureIds = new Set(fixtures.map((fixture) => fixture.id));
test('every contract rule has positive and negative fixtures with an explicit evidence type', () => {
  assert.deepEqual(catalog.rules.map((rule) => rule.id).sort(), [...schema.$defs.RuleId.enum].sort());
  assert.equal(fixtureIds.size, fixtures.length);
  for (const rule of catalog.rules) {
    assert.ok(rule.passFixtures.length > 0, rule.id);
    assert.ok(rule.failFixtures.length > 0, rule.id);
    for (const id of [...rule.passFixtures, ...rule.failFixtures]) assert.ok(fixtureIds.has(id), id);
  }
});
for (const example of read('../fixtures/tls/collection-errors.json')) {
  test('inconclusive fixture stays explicit: ' + example.name, () => {
    assert.equal(example.synthetic, true);
    const result = validateContract(example.schema, example.value);
    assert.equal(result.valid, true, JSON.stringify(result.errors));
    assert.equal(validateContract('Finding', example.value).valid, false);
  });
}
test('the design does not claim planned API operations are already implemented', () => {
  const api = read('../../packages/contracts/openapi.json');
  const operations = Object.values(api.paths).flatMap((path) => ['get', 'post', 'patch'].filter((method) => path[method]).map((method) => path[method]));
  const implemented = operations.filter((operation) => operation['x-implementation-status'] === 'implemented');
  assert.deepEqual(implemented.map((operation) => operation.operationId).sort(), ['getApiHealth', 'getApiReadiness', 'createAsset', 'listAssets', 'createScan', 'getScan'].sort());
});
