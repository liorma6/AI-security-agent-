import { createServiceApp } from '@ai-security/runtime';

export function createApp() {
  return createServiceApp({
    service: 'scanner',
    capabilities: { scanning: false, queueConsumer: false },
  });
}
