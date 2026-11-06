# TLS and HTTP evidence collection

Decision recorded November 6, 2026 for stage 4.

## Scope and entry points

Collection mode adds observations to the existing accepted-request, queue and worker flow. A request retains its execution mode. Pre-stage-4 requests with no mode continue as orchestration tests. POST /api/scans starts an authorized request and GET /api/scans/{scanId}/observations returns the bounded evidence set. The web dashboard is scheduled for stage 7.

The worker collects one TLS handshake and follows HTTP and authenticated HTTPS root responses. External DNS evidence and SSL Labs are marked unavailable pending stage 6, so the current scan ends partial. DNS resolution used for destination validation is operational network policy.

## Network policy

Every initial destination and redirect must use an exactly allowlisted hostname, HTTP port 80 or HTTPS port 443, and no URL credentials. The collector checks all returned A and AAAA addresses before choosing one. IP literals, loopback, private, link-local, multicast, documentation and other special-use addresses are rejected. IPv4-mapped IPv6 is classified by its embedded IPv4 address. IPv6 uses a conservative global-unicast policy excluding special-use and transition allocations.

The socket connects directly to the checked address. Host, SNI and certificate identity retain the logical hostname. Redirects are manual and every hop undergoes policy and DNS checks again. A changed DNS response cannot change an already pinned socket destination. One validated address is sampled per connection preparation. The result describes that endpoint.

| Limit | Value |
| --- | --- |
| Resolver timeout and tries | 2 seconds and one try |
| Maximum DNS answers | 16, all checked before selection |
| TLS or HTTP operation deadline | 5 seconds, including slow responses |
| Entire collection deadline | 30 seconds |
| Redirects per root request | 3 |
| HTTP headers / body | 16 KiB / 64 KiB |
| Serialized certificate chain | 8 certificates and 128 KiB DER |
| Persisted observations | At most 32 per scan |
| Worker concurrency | 2 |
| Starting-asset collection lease | One owner across workers, expires after 45 seconds |

MongoDB leases serialize scans of the same starting asset across workers. Lease acquisition waits up to 60 seconds before the queue retry policy applies. Redirected destinations are still subject to the per-operation limits and allowlist. Each collection attempt performs a bounded set of requests without an internal network retry loop. BullMQ handles failed worker attempts.

## Certificate and HTTP evidence

A dedicated evidence handshake permits inspection of an invalid certificate and records chain verification errors. SAN hostname matching is evaluated independently with Common Name fallback disabled. Evidence includes subject, issuer, DNS SANs, validity, DER certificate data, SHA-256 fingerprints, key type/size and signature algorithm.

The chain comes from Node's peer-certificate API and may include a root supplied by the selected trust store. A negotiated protocol and cipher describe that connection. Full protocol enumeration has a separate future evidence source.

HTTP uses its own verified connection. HTTPS failure retains the TLS evidence and produces an HTTP collection error. HSTS is recorded only from authenticated HTTPS. Plain HTTP HSTS is ignored. Response bodies are counted and discarded. An HTTP observation records the certificate fingerprint from its own connection, which can differ from the earlier TLS probe.

## Trust profiles

The default is Node's explicitly selected bundled CA list, labeled with the runtime version. Source operators may set TLS_TRUST_PROFILES_FILE to a local JSON file. Each profile contains an exact normalized hostname, a name and a PEM CA file path relative to that JSON file.

~~~json
{
  "your-authorized-domain.example": {
    "name": "approved-project-ca",
    "caFile": "./project-ca.pem"
  }
}
~~~

The custom CA replaces the trust roots for that hostname. The loader validates the CA at startup. Keep deployment-specific files outside Git. Container use requires an explicit read-only mount and the corresponding environment path in an operator-supplied Compose override.

## Atomic storage and compatibility

The bounded observations and terminal source summaries are committed together in one conditional MongoDB document update. The API reads observations from that committed document. Duplicate job deliveries retain the first terminal result. Interrupted collection can be retried without leaving a partially committed evidence set.

Contract 1.2.0 adds collection mode, observation listing, certificate and transport metadata, and collection error codes. Versions 1.0.0 and 1.1.0 continue to validate. Older records return an empty observation list.

## Verification and limits

The product collector is exercised against real loopback TLS/HTTP servers, including SNI selection, expiry, future validity, chain gaps, private trust, redirects, body/header limits and timeouts. DNS rebinding and mixed-family policy cases use explicitly controlled DNS answers. The public policy is checked before any fixture connection. The test-only lab policy grants access only to listeners created by that test run.

Integration uses actual MongoDB, Redis, API HTTP requests and two workers with the lab collector. It verifies atomic evidence, API restart, duplicate delivery, lease ownership/expiry and legacy jobs. The existing process-level recovery suite also remains enabled. Authorized live public-target acceptance will be recorded when a target is supplied.

Implementation follows [Node TLS](https://nodejs.org/docs/latest-v24.x/api/tls.html), [Node X509Certificate](https://nodejs.org/docs/latest-v24.x/api/crypto.html#class-x509certificate), [Node DNS](https://nodejs.org/docs/latest-v24.x/api/dns.html) and [OWASP SSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
