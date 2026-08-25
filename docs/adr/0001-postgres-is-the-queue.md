# Postgres is the queue

Indexing work was tracked in two places: `indexing_jobs` rows in Postgres and Celery task state in Redis, reconciled by polling `AsyncResult` — which allowed double-dispatch races and jobs whose truth lived only in Redis. We decided Postgres is the single authoritative queue: claiming a Job is an atomic `FOR UPDATE SKIP LOCKED` write against the existing `locked_by`/`locked_at` columns, and Celery/Redis exists only to wake executors; the beat poller keeps its cadence as the safety net.

## Considered Options

- **Redis/Celery owns the queue** (Postgres records outcomes only): rejected because it loses DB-backed crash recovery, splits pipeline state across systems, and rewrites scheduling for no capability gain.

## Consequences

- A worker crash mid-Job must be recoverable from Postgres alone: stale Claims are reclaimed by lock staleness, not by asking Redis.
- The dispatcher's job-state knowledge ('started'/'retry' status strings, ad-hoc dict payloads) is replaced by the Indexing Pipeline module's transitions.
