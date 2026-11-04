import { startServices } from './local-services.mjs';

let services;
try {
  services = await startServices();
  process.stdout.write('Workspace: http://127.0.0.1:' + services.ports.web + '\n');
  const interrupted = new Promise((resolve) => {
    process.once('SIGINT', () => resolve(null));
    process.once('SIGTERM', () => resolve(null));
  });
  const error = await Promise.race([services.failed, interrupted]);
  if (error) throw error;
} catch (error) {
  process.stderr.write(error.message + '\n');
  process.exitCode = 1;
} finally {
  await services?.stop();
}
