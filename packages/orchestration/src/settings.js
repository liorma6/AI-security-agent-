export function settings(env = process.env) {
  const mode = env.APP_MODE ?? 'bootstrap';
  if (!['bootstrap', 'orchestration_test'].includes(mode)) throw new Error('Invalid APP_MODE');
  const database = env.MONGO_DATABASE ?? 'ai_security';
  const queueName = env.QUEUE_NAME ?? 'scans';
  if (!/^[a-zA-Z0-9_-]{1,60}$/.test(database) || !/^[a-zA-Z0-9_-]{1,60}$/.test(queueName)) {
    throw new Error('Invalid database or queue name');
  }
  const result = {
    mode, database, queueName,
    mongoUrl: env.MONGO_URL ?? 'mongodb://127.0.0.1:27017',
    redisUrl: env.REDIS_URL ?? 'redis://127.0.0.1:6379',
    allowedTargets: env.ALLOWED_TARGETS ?? '',
  };
  if (!/^mongodb(\+srv)?:\/\//.test(result.mongoUrl) || !/^rediss?:\/\//.test(result.redisUrl)) {
    throw new Error('Invalid storage connection scheme');
  }
  return result;
}
