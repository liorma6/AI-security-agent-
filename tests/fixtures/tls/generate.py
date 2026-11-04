"""Generate disposable, loopback-only TLS lab material relative to the current UTC time."""
import argparse
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def name(value):
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, value)])


def key(bits=2048):
    return rsa.generate_private_key(public_exponent=65537, key_size=bits)


def issue(subject, public_key, issuer, issuer_key, start, end, *, ca=False, host=None):
    builder = (
        x509.CertificateBuilder()
        .subject_name(name(subject))
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(start)
        .not_valid_after(end)
        .add_extension(x509.BasicConstraints(ca=ca, path_length=1 if ca else None), True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(public_key), False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key()), False
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=not ca and isinstance(public_key, rsa.RSAPublicKey),
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=ca,
                crl_sign=ca,
                encipher_only=None,
                decipher_only=None,
            ),
            True,
        )
    )
    if host:
        builder = builder.add_extension(x509.SubjectAlternativeName([x509.DNSName(host)]), False)
        builder = builder.add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), False
        )
    return builder.sign(issuer_key, hashes.SHA256())


def write_key(path, private_key):
    path.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    path.chmod(0o600)


def pem(cert):
    return cert.public_bytes(serialization.Encoding.PEM)


def generate(output, now):
    output.mkdir(parents=True, exist_ok=True)
    root_key, private_root_key, intermediate_key, leaf_key = key(3072), key(3072), key(), key()
    start, end = now - timedelta(days=365), now + timedelta(days=3650)
    root = issue("Disposable lab root", root_key.public_key(), name("Disposable lab root"),
                 root_key, start, end, ca=True)
    private_root = issue("Disposable private root", private_root_key.public_key(),
                         name("Disposable private root"), private_root_key, start, end, ca=True)
    intermediate = issue("Disposable intermediate", intermediate_key.public_key(),
                         root.subject, root_key, start, end, ca=True)
    for filename, cert in [("root.pem", root), ("private-root.pem", private_root),
                           ("intermediate.pem", intermediate)]:
        (output / filename).write_bytes(pem(cert))
    write_key(output / "root-key.pem", root_key)
    cases = {
        "valid": (-1, 90, "valid.lab.test", leaf_key, root, root_key),
        "expired": (-30, -1, "valid.lab.test", leaf_key, root, root_key),
        "future": (1, 90, "valid.lab.test", leaf_key, root, root_key),
        "expiring": (-1, 7, "valid.lab.test", leaf_key, root, root_key),
        "wrong-host": (-1, 90, "other.lab.test", leaf_key, root, root_key),
        "chain": (-1, 90, "valid.lab.test", leaf_key, intermediate, intermediate_key),
        "private": (-1, 90, "valid.lab.test", leaf_key, private_root, private_root_key),
        "weak-key": (-1, 90, "valid.lab.test", key(1024), root, root_key),
        "ec": (-1, 90, "valid.lab.test", ec.generate_private_key(ec.SECP256R1()), root, root_key),
    }
    certificates = {}
    for case, (before, after, hostname, leaf, issuer_cert, signing_key) in cases.items():
        cert = issue(hostname, leaf.public_key(), issuer_cert.subject, signing_key,
                     now + timedelta(days=before), now + timedelta(days=after), host=hostname)
        (output / (case + ".pem")).write_bytes(pem(cert))
        write_key(output / (case + "-key.pem"), leaf)
        certificates[case] = {
            "sha256": cert.fingerprint(hashes.SHA256()).hex(),
            "notBefore": cert.not_valid_before_utc.isoformat(),
            "notAfter": cert.not_valid_after_utc.isoformat(),
            "hostname": hostname,
        }
    (output / "chain-full.pem").write_bytes((output / "chain.pem").read_bytes() + pem(intermediate))

    # OpenSSL's CLI can sign this deliberately obsolete test fixture.
    # It is only inspected offline; no TLS listener weakens policy to load it.
    openssl = os.environ.get("OPENSSL_BIN") or shutil.which("openssl")
    if not openssl:
        raise RuntimeError("OpenSSL 3.x is required; add it to PATH or set OPENSSL_BIN")
    csr = x509.CertificateSigningRequestBuilder().subject_name(name("valid.lab.test"))
    csr = csr.add_extension(
        x509.SubjectAlternativeName([x509.DNSName("valid.lab.test")]), False
    ).sign(leaf_key, hashes.SHA256())
    (output / "sha1.csr").write_bytes(csr.public_bytes(serialization.Encoding.PEM))
    subprocess.run([
        openssl, "x509", "-req", "-in", str(output / "sha1.csr"),
        "-CA", str(output / "root.pem"), "-CAkey", str(output / "root-key.pem"),
        "-set_serial", str(x509.random_serial_number()), "-days", "30", "-sha1",
        "-copy_extensions", "copy", "-out", str(output / "sha1.pem"),
    ], check=True, capture_output=True)
    sha1 = x509.load_pem_x509_certificate((output / "sha1.pem").read_bytes())
    certificates["sha1"] = {
        "sha256": sha1.fingerprint(hashes.SHA256()).hex(),
        "signature": sha1.signature_hash_algorithm.name,
        "dateSource": "OpenSSL current UTC clock; checked offline for signature only",
    }
    manifest = {
        "generatedAt": now.isoformat(), "purpose": "disposable-local-test-fixtures",
        "certificates": certificates,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = generate(args.out.resolve(), datetime.now(UTC).replace(microsecond=0))
    print(json.dumps({
        "generatedAt": result["generatedAt"], "certificates": len(result["certificates"])
    }))
