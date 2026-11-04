import { readPort, serve } from '@ai-security/runtime';
import { createApp } from './app.js';

serve(createApp(), {
  service: 'api',
  port: readPort(process.env.PORT ?? process.env.API_PORT, 3001),
  host: process.env.HOST ?? '127.0.0.1',
});
