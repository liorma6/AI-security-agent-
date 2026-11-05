# TLS and HTTPS assessment policy

Policy version 1.0.0 defines the rule engine planned for stage 5. Each rule below links to known-good and known-bad fixture IDs in the lab. The severities are project policy ratings. The machine-readable definitions and thresholds live in the [rule catalog](../packages/contracts/policy/rules.json).

| Rule | Failure condition | Severity | Passing fixtures | Failing fixtures |
| --- | --- | --- | --- | --- |
| TLS-EXPIRED | Certificate expiry is at or before measurement time. | High | valid | expired |
| TLS-NOT-YET-VALID | Validity begins after measurement time. | High | valid | future |
| TLS-EXPIRING | A currently valid certificate expires within 30 days. | Low | valid | expiring |
| TLS-HOSTNAME | SAN fails to match the requested hostname with the correct SNI. | High | valid, sni | wrong-host |
| TLS-TRUST | Chain verification fails against the selected trust profile. | High | valid, chain-complete, private-approved | chain-missing, private-untrusted |
| TLS-KEY-STRENGTH | RSA is below 2048 bits or EC below 256 bits. | High | valid, ec | weak-key (offline) |
| TLS-SIGNATURE | Certificate signature uses MD5 or SHA-1. | High | valid | sha1 (offline) |
| TLS-LEGACY-PROTOCOL | Endpoint accepts TLS 1.0 or 1.1. | High | modern-protocol | legacy-protocol |
| HTTPS-REDIRECT | HTTP root responds without a valid redirect to an authorized HTTPS endpoint. | Medium | redirect | no-redirect |
| HTTPS-HSTS | Authenticated HTTPS root response lacks a valid positive HSTS max-age. | Low | valid | hsts-missing, hsts-invalid, hsts-disabled |

The policy accepts RSA and EC keys at or above the size threshold and recognized Ed25519 keys. Permitted signatures include SHA-256, SHA-384, SHA-512 and Ed25519. An unrecognized algorithm yields unknown. [TLS recommendations, RFC 9325](https://www.rfc-editor.org/rfc/rfc9325.html).

## Interpreting results

A RuleResult is pass, fail, unknown or not_applicable. Only a fail can create a Finding, which requires evidence, severity and remediation. Return unknown for a timeout, DNS failure, unavailable provider or evidence that cannot support the decision. Give an explicit reason for not_applicable. For example, the near-expiry reminder is inapplicable to a certificate that has already expired.

A single negotiated protocol describes one connection. To pass the legacy-protocol check, confirm a working modern connection and explicit protocol-version rejections for both legacy versions, or obtain complete, reliable enumeration from a provider. A timeout during a legacy probe leaves support inconclusive. [TLS 1.0 and 1.1 deprecation, RFC 8996](https://www.rfc-editor.org/rfc/rfc8996.html).

Read HSTS from an authenticated HTTPS response. A max-age of zero disables HSTS. This rule evaluates the root response. Preload enrollment and a site-wide audit are separate assessments. [HTTP Strict Transport Security, RFC 6797](https://www.rfc-editor.org/rfc/rfc6797.html).

## Host identity and trust

Use the operator-approved normalized hostname for SNI and compare SAN against that name. Record the IP address separately. Evaluate hostname and chain independently. The public default will use an identified runtime trust store. Bind an explicitly approved private CA to its target's trust profile. The lab demonstrates acceptance and rejection of the same certificate under different trust profiles.

## Allowed destinations

The public path is limited to server-authorized targets, HTTP/HTTPS, and ports 80 and 443. The Endpoint schema also represents ephemeral lab ports. Runtime authorization is a separate check.

Stages 3 and 4 will validate every A and AAAA result, including IPv4-mapped IPv6, and block loopback, private, link-local, special and other non-public addresses. Pin the connection to the checked address, preserve Host and SNI, and revalidate every redirect within a bounded hop count.

The fixture harness uses listeners created by the current run on 127.0.0.1 and their allocated ports. The lab is isolated from the public scan path. The [fixture guide](../tests/fixtures/tls/README.md) describes live, offline and synthetic evidence.
