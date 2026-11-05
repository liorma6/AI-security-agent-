import express from 'express';

export function createServiceApp({ service, capabilities, healthPaths = ['/health'], stage = 1, mode = 'bootstrap', configure = () => {} }) {
  const app = express();
  app.disable('x-powered-by');
  for (const path of healthPaths) {
    app.get(path, (_req, res) => {
      res.set('Cache-Control', 'no-store').json({
        status: 'ok',
        service,
        version: '0.1.0',
        stage,
        mode,
        capabilities,
      });
    });
  }
  configure(app);
  app.use((_req, res) => res.status(404).json({ error: 'not_found' }));
  return app;
}

export function readPort(value, fallback) {
  const port = Number(value ?? fallback);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error('Port must be an integer between 1 and 65535');
  }
  return port;
}

export function serve(app, { service, port, host = '127.0.0.1', onClose = async () => {} }) {
  const server = app.listen(port, host, () => {
    process.stdout.write(JSON.stringify({ event: 'listening', service, host, port }) + '\n');
  });
  server.on('error', (error) => {
    process.stderr.write(JSON.stringify({ event: 'server_error', service, code: error.code }) + '\n');
    process.exitCode = 1;
  });
  const shutdown = () => {
    server.close(async () => { await onClose(); process.exit(0); });
    server.closeIdleConnections();
    setTimeout(() => process.exit(1), 5000).unref();
  };
  process.once('SIGINT', shutdown);
  process.once('SIGTERM', shutdown);
  return server;
}
