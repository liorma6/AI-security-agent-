import { readPort, serve } from '@ai-security/runtime';
import { settings } from '@ai-security/orchestration/settings';
import { openStore } from '@ai-security/orchestration/storage';
import { createQueue, startWorker } from '@ai-security/orchestration/queue';
import { createApp } from './app.js';

const config = settings();
let store;
let queue;
let background;
try {
  if (config.mode !== 'bootstrap') {
    store = await openStore(config);
    queue = createQueue(config);
    background = startWorker(store, config, { delayMs: process.env.NODE_ENV === 'test' ? Number(process.env.TEST_WORK_DELAY_MS ?? 0) : 0 });
  }
  serve(createApp({ store, queue, worker: background, mode: config.mode }), {
    service: 'scanner', port: readPort(process.env.PORT ?? process.env.SCANNER_PORT, 3002),
    host: process.env.HOST ?? '127.0.0.1',
    async onClose() { await background?.close(); await queue?.close(); await store?.close(); },
  });
} catch (error) {
  console.error(JSON.stringify({ event: 'startup_failed', service: 'scanner', code: error.code ?? error.name }));
  await background?.close(); await queue?.close(); await store?.close();
  process.exitCode = 1;
}
