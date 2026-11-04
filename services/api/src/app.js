import { createServiceApp } from '@ai-security/runtime';

export function createApp() {
  return createServiceApp({
    service: 'api',
    healthPaths: ['/health', '/api/health'],
    capabilities: { scanning: false, persistence: false },
  });
}
