import { readPort, serve } from '@ai-security/runtime';
import { settings } from '@ai-security/orchestration/settings';
import { openStore } from '@ai-security/orchestration/storage';
import { createQueue, startDispatcher } from '@ai-security/orchestration/queue';
import { createApp } from './app.js';

const config = settings();
let store;
let queue;
let background;
try {
  if (config.mode !== 'bootstrap') {
    store = await openStore(config);
    queue = createQueue(config);
    background = startDispatcher(store, queue.queue);
  }
  serve(createApp({ store, queue, allowedTargets: config.allowedTargets, mode: config.mode }), {
    service: 'api', port: readPort(process.env.PORT ?? process.env.API_PORT, 3001),
    host: process.env.HOST ?? '127.0.0.1',
    async onClose() { await background?.close(); await queue?.close(); await store?.close(); },
  });
} catch (error) {
  console.error(JSON.stringify({ event: 'startup_failed', service: 'api', code: error.code ?? error.name }));
  await background?.close(); await queue?.close(); await store?.close();
  process.exitCode = 1;
}
