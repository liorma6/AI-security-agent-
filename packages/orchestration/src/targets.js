import { domainToASCII } from 'node:url';
import { isIP } from 'node:net';
import { validateContract } from '@ai-security/contracts';

export class RequestError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export function normalizeHostname(input) {
  if (typeof input !== 'string' || input.length > 2048) {
    throw new RequestError(400, 'invalid_request', 'Supply a hostname or an HTTP(S) root URL.');
  }
  let hostname = input.trim();
  if (/^https?:\/\//i.test(hostname)) {
    let url;
    try { url = new URL(hostname); } catch {
      throw new RequestError(400, 'invalid_request', 'The URL is invalid.');
    }
    if (url.username || url.password || url.search || url.hash || url.pathname !== '/' ||
        (url.port && !['80', '443'].includes(url.port))) {
      throw new RequestError(400, 'invalid_request', 'Use a root URL on port 80 or 443 without credentials, query or fragment.');
    }
    hostname = url.hostname;
  }
  hostname = domainToASCII(hostname.toLowerCase().replace(/\.$/, ''));
  if (isIP(hostname) || !validateContract('Hostname', hostname).valid ||
      /(^|\.)(localhost|local|internal|home|lan|onion)$/.test(hostname)) {
    throw new RequestError(400, 'invalid_request', 'Use a public DNS hostname.');
  }
  return hostname;
}

export function targetPolicy(value = '') {
  const allowed = new Set(value.split(',').map(s => s.trim()).filter(Boolean).map(normalizeHostname));
  return {
    authorize(hostname) {
      if (!allowed.has(hostname)) {
        throw new RequestError(403, 'forbidden_target', 'The operator must add this exact hostname to ALLOWED_TARGETS.');
      }
      return hostname;
    },
  };
}
