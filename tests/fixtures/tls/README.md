# Local TLS laboratory

This is a test fixture system, not the production scanner. It binds only to 127.0.0.1 on OS-assigned ports and never calls public targets.

## Prerequisites and use

Install the repository's Node dependencies and Python development dependencies using the root README. OpenSSL 3.x must be on PATH, or OPENSSL_BIN must point to its executable. On Windows, Git for Windows may provide it under its usr/bin directory. Do not change system TLS policy or import the lab CA into the operating system.

- npm run lab:generate — create disposable certificates in generated/.
- npm run lab — regenerate certificates, start listeners and write generated/endpoints.json.
- npm run test:lab — regenerate fixtures, verify their behavior and stop all listeners.

Stop the interactive lab with Ctrl+C. Ports change each run. Tests connect to 127.0.0.1 with the logical hostname valid.lab.test passed explicitly as SNI and Host; they do not modify hosts files or DNS.

## Fixture types

cases.json distinguishes live HTTPS/HTTP/TCP scenarios, offline certificates and explicitly synthetic collection errors. The rule coverage matrix is packages/contracts/policy/rules.json. The lab does not run the future rules engine.

Valid certificates expire 90 days after generation; the expiring certificate expires in 7 days. Expired and future certificates are generated with relative validity windows. CAs are disposable and generated each run. Fingerprints and keys change; the expected behavior is reproducible, not identical certificate bytes.

OpenSSL generates the SHA-1 fixture relative to its current clock. That fixture is checked offline for signature properties only. The weak RSA 1024 certificate is also checked offline because modern TLS policy may reject loading it. Legacy TLS 1.0 is enabled only on the designated loopback test listener and its explicit test client; other clients and services retain their defaults.

The SNI listener defaults to the wrong-host certificate and selects the valid certificate only for the expected SNI. The chain cases use the same leaf with and without the intermediate. The private-CA cases demonstrate explicit trust profiles.

generated/ contains unencrypted disposable private keys and is excluded from Git and Docker build contexts. These files are never production credentials and must not be reused outside this lab.

## What the tests establish

Tests check certificate dates, hostname mismatch, SNI behavior, chain completeness, explicit private trust, RSA/EC key properties, an actual SHA-1 signed certificate, protocol negotiation, redirect/HSTS headers and a stalled handshake.

Synthetic DNS/provider errors are contract fixtures, not live integrations. A passing lab test proves the fixture's behavior; it does not yet prove that the stage 4 scanner or stage 5 risk engine is implemented.
