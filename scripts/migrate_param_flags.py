#!/usr/bin/env python3
"""
One-off: recompute prompts.*_enabled from numeric columns (idempotent).
Run after alembic upgrade if you need to fix drift. The Alembic revision
k5m6n7o8p9qb already applies the same UPDATE on upgrade.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text  # noqa: E402
from app.config import settings  # noqa: E402


def main() -> None:
    url = settings.SUPABASE_DB_URL or os.environ.get("SUPABASE_DB_URL")
    if not url:
        print("SUPABASE_DB_URL not set", file=sys.stderr)
        sys.exit(1)
    engine = create_engine(url)
    sql = text(
        """
        UPDATE prompts SET
          max_tokens_enabled = (max_tokens IS NOT NULL AND max_tokens > 0),
          temperature_enabled = (
            temperature IS NOT NULL AND abs(temperature - 0.7) > 0.0001
          ),
          frequency_penalty_enabled = (
            frequency_penalty IS NOT NULL AND abs(frequency_penalty) > 0.0001
          ),
          presence_penalty_enabled = (
            presence_penalty IS NOT NULL AND abs(presence_penalty) > 0.0001
          ),
          top_p_enabled = (
            top_p IS NOT NULL AND abs(top_p - 1.0) > 0.0001
          )
        """
    )
    with engine.connect() as conn:
        result = conn.execute(sql)
        conn.commit()
        print(f"Updated rows: {result.rowcount}")


if __name__ == "__main__":
    main()
