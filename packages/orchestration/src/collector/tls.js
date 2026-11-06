import tls from 'node:tls';
import { X509Certificate } from 'node:crypto';
import { CollectionError, limits } from './policy.js';

export function certificate(raw) {
  const x509 = new X509Certificate(raw);
  const key = x509.publicKey;
  const types = { rsa: 'RSA', 'rsa-pss': 'RSA', ec: 'EC', ed25519: 'Ed25519' };
  const curves = { prime256v1: 256, secp256k1: 256, secp384r1: 384, secp521r1: 521 };
  const sans = [...(x509.subjectAltName ?? '').matchAll(/(?:^|, )DNS:("(?:[^"\\]|\\.)*"|[^,]*)/g)]
    .map(match => match[1].startsWith('"') ? JSON.parse(match[1]) : match[1]);
  return {
    sha256: x509.fingerprint256.replaceAll(':', '').toLowerCase(),
    subject: x509.subject, issuer: x509.issuer, sans,
    notBefore: x509.validFromDate.toISOString(), notAfter: x509.validToDate.toISOString(),
    keyType: types[key.asymmetricKeyType] ?? 'other',
    keyBits: key.asymmetricKeyDetails?.modulusLength ?? curves[key.asymmetricKeyDetails?.namedCurve] ??
      (key.asymmetricKeyType === 'ed25519' ? 256 : 0),
    signatureAlgorithm: x509.signatureAlgorithm ?? x509.signatureAlgorithmOid,
    derBase64: raw.toString('base64'),
  };
}

export function verifyHostname(hostname, peer) {
  if (!new X509Certificate(peer.raw).checkHost(hostname, { subject: 'never' })) {
    return Object.assign(new Error('The certificate SAN does not match the authorized hostname.'), { code: 'ERR_TLS_CERT_ALTNAME_INVALID' });
  }
}

export function collectTls(target, trust, signal, bounds = limits) {
  return new Promise((resolve, reject) => {
    // This evidence-only handshake retains verification errors for invalid certificates.
    // HTTP uses a separate authenticated connection with rejectUnauthorized enabled.
    const socket = tls.connect({
      host: target.address, port: target.port, family: target.family, autoSelectFamily: false,
      servername: target.hostname, ca: trust.ca, minVersion: 'TLSv1.2',
      rejectUnauthorized: false, checkServerIdentity: () => undefined,
      ALPNProtocols: ['http/1.1'], signal,
    });
    const timer = setTimeout(() => socket.destroy(new CollectionError('timeout', 'TLS handshake exceeded its time limit.')), bounds.requestMs);
    socket.once('error', reject);
    socket.once('close', () => clearTimeout(timer));
    socket.once('secureConnect', () => {
      try {
        const peer = socket.getPeerCertificate(true);
        const chain = [];
        const seen = new Set();
        let current = peer;
        let bytes = 0;
        while (current?.raw) {
          bytes += current.raw.length;
          if (chain.length >= bounds.maxChainLength || bytes > bounds.maxCertificateBytes) {
            throw new CollectionError('response_too_large', 'The certificate chain exceeded the collection limit.');
          }
          const item = certificate(current.raw);
          if (seen.has(item.sha256)) break;
          chain.push(item);
          seen.add(item.sha256);
          current = current.issuerCertificate;
        }
        if (!chain.length) throw new CollectionError('invalid_response', 'The peer supplied no certificate.');
        const hostnameError = verifyHostname(target.hostname, peer);
        const errors = [socket.authorizationError, hostnameError?.code].filter(Boolean).map(String);
        resolve({
          certificate: chain[0], certificates: chain, chainSha256: chain.map(item => item.sha256),
          trustProfile: trust.name, chainAuthorized: socket.authorized, hostnameMatches: !hostnameError,
          authorized: socket.authorized && !hostnameError, authorizationErrors: errors,
          negotiatedProtocol: socket.getProtocol(), negotiatedCipher: socket.getCipher().standardName ?? socket.getCipher().name,
          supportedProtocols: null, enumerationComplete: false,
        });
      } catch (error) { reject(error); }
      finally { socket.destroy(); }
    });
  });
}
