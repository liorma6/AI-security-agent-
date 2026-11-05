# Durable scan orchestration

Decision recorded November 5, 2026 for stage 3.

## Storage and dispatch

An accepted scan is one MongoDB document containing the public state, idempotency key and internal dispatch schedule. The insert uses majority acknowledgement and journaling. The API returns 202 only after this write. An indexed dispatcher claims due requests in small batches and publishes the scan UUID as the BullMQ job ID.

A five-second dispatch schedule makes a failed publish eligible for another attempt. A second API process can continue dispatch after the first exits. Every incomplete request remains eligible until a terminal result has been recorded. Lost Redis queue state can therefore be rebuilt from MongoDB.

## Concurrency and recovery

MongoDB enforces a unique normalized asset hostname and a unique request key. A key reused with the original asset returns the existing scan. A different asset yields 409. Pagination uses an indexed UUID cursor and a bounded limit.

BullMQ owns active job locks and stalled-job recovery. The worker records each processing attempt and rechecks the target's allowlist entry. It commits its terminal state and source results in one conditional MongoDB update. Duplicate deliveries see terminal state and return. Competing completions can commit at most one result. Retry exhaustion becomes a durable failed result during reconciliation.

Queue delivery is at least once. Future collectors must preserve idempotence for their own observation writes and bounded external actions. The stage 3 processor performs an explicitly marked orchestration test, records every security source as unavailable and finishes partial.

## Runtime choices and limits

The pinned clients are MongoDB driver 7.8.0, BullMQ 5.81.5 and ioredis 5.11.1. The BullMQ 5 connection model matches the direct ioredis clients used here. Producer commands fail promptly when Redis is unavailable. Worker connections reconnect. Redis uses AOF persistence and noeviction in Compose.

The queue retains up to 1,000 completed and failed jobs. MongoDB remains the durable record of accepted scans and terminal results. A single local operator controls the allowlist. Public-target DNS resolution, address pinning and redirect validation are part of the collector stage.

The API and worker expose liveness separately from /ready. A degraded Redis connection still permits MongoDB-backed acceptance. A MongoDB startup failure stops the service. These settings target the local project deployment. High-load limits and long-term retention policies require the later load and delivery stages.

## Verification

Integration checks use real MongoDB and Redis, two API processes, actual HTTP requests, a TCP proxy for queue outages and forced worker termination. The checks verify durable records, stable request IDs, one committed result, recovered stalled work and authorization checked again at processing time.

References are the [BullMQ connection guidance](https://docs.bullmq.io/guide/connections), [job IDs](https://docs.bullmq.io/guide/jobs/job-ids), [stalled jobs](https://docs.bullmq.io/guide/workers/stalled-jobs) and [MongoDB updates](https://www.mongodb.com/docs/drivers/node/current/crud/update/).
