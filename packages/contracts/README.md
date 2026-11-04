# Contracts

Schema and policy version **1.0.0**, introduced in stage 2. The application still exposes only its bootstrap health endpoints; these files define the interfaces for later stages.

- [JSON Schema 2020-12](schemas/contracts.schema.json): Asset, Scan, Observation, RuleResult, Finding, Feedback, ModelVersion and request/response types.
- [OpenAPI 3.1.2](openapi.json): public API and the internal ML interface. Each operation states its implementation status and intended stage. Only health is implemented.
- [Rule policy](policy/rules.json): ten rules, severity, pass/fail conditions and fixture references. This is a specification, not the stage 5 rule engine.
- [Valid](examples/valid.json) and [invalid](examples/invalid.json) examples: shared between JavaScript and Python tests. Fixed timestamps here illustrate wire formats; lab certificates use relative dates.

## Validation

```js
import { validateContract } from '@ai-security/contracts';

const { valid, errors } = validateContract('CreateAssetRequest', {
  hostname: 'example.com',
});
```

The Node.js validator uses strict Ajv without coercion, defaults or deletion of submitted fields. Python tests load the same schema using Draft202012Validator with format checking. Run `npm test`, `npm run check:openapi` and `uv run --project services/ml --frozen pytest services/ml` from the repository root.

## Meaning and limits

An Observation records endpoint, source and measurement time. A failed collection has an error and no successful evidence. A successful observation must carry the correct evidence type for its source. Only a failed RuleResult becomes a Finding; unknown is never a vulnerability. Human feedback separates true_positive, false_positive and uncertain from treatment states such as resolved and accepted_risk. An abstaining model returns no score.

Request objects cannot grant authorization. Authorization belongs to server policy. Hostnames on the wire must already be normalized lower-case ASCII DNS names; a future UI may extract a hostname from a URL before submission. Public scanning is limited to ports 80/443 by future runtime policy, while Endpoint allows laboratory ports.

Schema validation checks structure, types, formats and selected state invariants. It does **not** prove ownership, reference existence, timestamp ordering across records, permissible state transitions, DNS safety, model quality or completeness of a provider's evidence. Those checks belong to later service implementations. This package is not yet wired into business endpoints because those endpoints do not exist.

Breaking field or meaning changes require a new major schema version and matching examples. Additive changes require coordinated producer/consumer updates: additional properties are rejected deliberately. Versioned observations and policies must remain interpretable after later changes.
