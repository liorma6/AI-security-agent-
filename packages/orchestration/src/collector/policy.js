import { Resolver } from 'node:dns/promises';
import { isIP } from 'node:net';
import ipaddr from 'ipaddr.js';
import { normalizeHostname, targetPolicy } from '../targets.js';

export class CollectionError extends Error {
  constructor(code, message) { super(message); this.code = code; }
}

export const limits = Object.freeze({
  dnsMs: 2000, requestMs: 5000, scanMs: 30000, maxAddresses: 16,
  maxRedirects: 3, maxHeaderBytes: 16384, maxBodyBytes: 65536,
  maxCertificateBytes: 131072, maxChainLength: 8,
});

export function publicAddress(value) {
  if (!isIP(value) || value.includes('%')) return false;
  let address = ipaddr.parse(value);
  if (address.isIPv4MappedAddress?.()) address = address.toIPv4Address();
  if (address.range() !== 'unicast') return false;
  // Conservatively exclude special-use IPv6 allocations and transition mechanisms.
  return address.kind() === 'ipv4' ||
    (address.match(ipaddr.parseCIDR('2000::/3')) &&
     !address.match(ipaddr.parseCIDR('2001::/23')) &&
     !address.match(ipaddr.parseCIDR('2002::/16')));
}

export async function resolveAddresses(hostname, signal) {
  const resolver = new Resolver({ timeout: limits.dnsMs, tries: 1 });
  const cancel = () => resolver.cancel();
  signal?.throwIfAborted();
  signal?.addEventListener('abort', cancel, { once: true });
  try {
    const results = await Promise.allSettled([resolver.resolve4(hostname), resolver.resolve6(hostname)]);
    signal?.throwIfAborted();
    const addresses = [];
    for (const result of results) {
      if (result.status === 'fulfilled') addresses.push(...result.value);
      else if (!['ENODATA', 'ENOTFOUND'].includes(result.reason.code)) {
        throw new CollectionError('dns_error', 'A DNS address family could not be checked.');
      }
    }
    if (!addresses.length) throw new CollectionError('dns_error', 'DNS returned no address records.');
    return addresses;
  } finally { signal?.removeEventListener('abort', cancel); }
}

export function createNetworkPolicy(allowedTargets, resolve = resolveAddresses) {
  const allowlist = targetPolicy(allowedTargets);
  return {
    async prepare(value, signal) {
      let url;
      try {
        url = new URL(value);
        if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password ||
            url.hash || url.href.length > 2048 || url.port ||
            /[\\\r\n]/.test(value)) throw new Error('Invalid URL');
        url.hostname = normalizeHostname(url.hostname);
        allowlist.authorize(url.hostname);
      } catch {
        throw new CollectionError('target_blocked', 'The destination is outside the authorized HTTP/HTTPS policy.');
      }
      const answers = await resolve(url.hostname, signal);
      if (!answers.length || answers.length > limits.maxAddresses || answers.some(address => !publicAddress(address))) {
        throw new CollectionError('target_blocked', 'Every DNS answer must be a permitted public address.');
      }
      const address = answers.find(address => isIP(address) === 4) ?? answers[0];
      return { url: url.href, hostname: url.hostname, address, family: isIP(address),
        port: url.protocol === 'https:' ? 443 : 80, protocol: url.protocol,
        path: url.pathname + url.search, authority: url.host };
    },
  };
}

export function errorDetails(error) {
  if (error instanceof CollectionError) return { code: error.code, message: error.message };
  if (['AbortError', 'TimeoutError'].includes(error.name) || error.code === 'ETIMEDOUT') {
    return { code: 'timeout', message: 'The collection deadline was reached.' };
  }
  if (error.code === 'ECONNREFUSED') return { code: 'connection_refused', message: 'The destination refused the connection.' };
  if (/CERT|SELF_SIGNED|UNABLE_TO_VERIFY|ISSUER|ALTNAME/.test(error.code ?? '')) {
    return { code: 'tls_verification_error', message: 'HTTPS certificate verification failed.' };
  }
  if (/SSL|TLS/.test(error.code ?? '')) return { code: 'tls_handshake_error', message: 'The TLS handshake could not complete.' };
  return { code: 'invalid_response', message: 'The endpoint did not return a usable bounded response.' };
}
