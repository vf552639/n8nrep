---
description: How to create Alembic migrations correctly
---

# Alembic Migration Workflow

## Before Creating a Migration

1. **Always check current head first:**
   ```bash
   docker-compose exec web alembic heads
   ```

2. **Ensure there is exactly ONE head.** If there are multiple heads, merge them first:
   ```bash
   docker-compose exec web alembic merge <head1> <head2> -m "merge_description"
   ```

3. **Check current revision in DB:**
   ```bash
   docker-compose exec web alembic current
   ```

## Creating a Migration

### Auto-generated (preferred):
```bash
docker-compose exec web alembic revision --autogenerate -m "description_of_changes"
```

### Manual:
- Set `down_revision` to the **current single head** (NOT an older revision)
- Verify with `alembic heads` beforehand

> ⚠️ **CRITICAL**: Never set `down_revision` to a parent of the current head. This creates branch forks requiring a merge migration. Always point to the latest head.

## Applying Migration

```bash
docker-compose exec web alembic upgrade head
```

## Verifying

```bash
docker-compose exec web alembic heads    # Should show exactly 1 head
docker-compose exec web alembic current  # Should match the head
```

## Troubleshooting

- If `alembic upgrade head` fails with `statement_timeout` or `lock timeout`, another session is holding a lock on the objects being migrated. Inspect blocking activity:

  ```sql
  SELECT pid, application_name, state, now() - xact_start AS tx_duration, query
  FROM pg_stat_activity
  WHERE state <> 'idle'
  ORDER BY xact_start;
  ```

- To terminate long-lived `idle in transaction` sessions (e.g. stuck pooler connections older than 5 minutes):

  ```sql
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE state = 'idle in transaction'
    AND xact_start < now() - interval '5 minutes';
  ```

- Split large migrations into separate revisions: one revision for DDL only, a follow-up for data `UPDATE`/`INSERT`. That reduces the chance a single long transaction hits timeouts while waiting for locks.

- On app startup, the API logs either `Alembic migrations up to date: <rev>` or a **migration mismatch** banner if `alembic current` ≠ `alembic heads` — fix with `docker-compose exec web alembic upgrade head` before relying on endpoints that touch new schema.
