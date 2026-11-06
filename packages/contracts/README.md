# Shared contracts

Contract version **1.2.0** defines JSON Schema 2020-12 data structures and an OpenAPI 3.1.2 interface. Policy version remains 1.0.0. The schema continues to validate existing 1.0.0 and 1.1.0 records. Version 1.2 adds collection mode, an observation list, certificate/transport metadata and bounded collection errors.

The API implements asset creation/listing and scan submission/status and observation listing in collection and orchestration_test modes. OpenAPI identifies later-stage operations as planned. The [rule catalog](policy/rules.json) specifies ten rules and their fixtures. [Schema](schemas/contracts.schema.json) and [OpenAPI](openapi.json).

## Validation

```js
import { validateContract } from '@ai-security/contracts';

const result = validateContract('CreateAssetRequest', {
  hostname: 'demo.example.com',
});
```

Node uses strict Ajv with formats and without coercion or deletion of fields. Python tests load the same source with Draft202012Validator and explicit format checks. The [accepted](examples/valid.json) and [rejected](examples/invalid.json) examples run in both languages.

CreateAssetRequest accepts a hostname or HTTP(S) root URL. Service validation normalizes it, validates the resulting Hostname contract and checks the exact server allowlist. Public Asset records always contain a normalized DNS name. Request fields cannot grant authorization.

## Record semantics

An Observation identifies its source, endpoint and times. Successful evidence must match the source. A collection failure carries an error. Only a failed RuleResult becomes a Finding with evidence and remediation. Reviewer truth labels are separate from treatment state. An abstaining model supplies no score.

Scan has an optional executionMode field to support existing 1.0.0 records. New requests record the configured execution mode at acceptance. Collection observations retain their own endpoint, certificate identity and measurement time. Version 1.2 HTTP evidence permits HSTS only when authenticated is true. Persistence, authorization, request-key consistency and state transitions are enforced in the services. The schema checks shapes, formats and selected state invariants.

Breaking semantic or field changes require a new major schema version. Additive versions require coordinated producer and consumer updates because extra fields are rejected. Keep previous observations and their policies interpretable.
