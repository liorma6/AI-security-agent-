import { readPort, serve } from '@ai-security/runtime';
import { createApp } from './app.js';

serve(createApp(), {
  service: 'scanner',
  port: readPort(process.env.PORT ?? process.env.SCANNER_PORT, 3002),
  host: process.env.HOST ?? '127.0.0.1',
});
