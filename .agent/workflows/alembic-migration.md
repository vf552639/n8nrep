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
