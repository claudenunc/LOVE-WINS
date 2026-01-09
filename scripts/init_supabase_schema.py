"""
Init Supabase schema helper

Usage:
  - Set environment variable `DATABASE_URL` (Postgres URL for Supabase DB).
  - Run: `python scripts/init_supabase_schema.py`

This script executes the SQL in `migrations/0001_create_projects.sql` against the DATABASE_URL.
"""

import os
import sys
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set. Example: postgresql://user:pass@host:5432/dbname")
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 is required. Install with: pip install psycopg2-binary")
        sys.exit(1)

    if not MIGRATIONS_DIR.exists():
        print(f"ERROR: migrations directory not found: {MIGRATIONS_DIR}")
        sys.exit(1)

    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not sql_files:
        print("No migration files found in migrations/")
        sys.exit(0)

    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cur = conn.cursor()

        for f in sql_files:
            print(f"Running migration: {f.name}")
            sql = f.read_text()
            cur.execute(sql)

        cur.close()
        conn.close()
        print("All migrations executed successfully.")
    except Exception as e:
        print("Failed to execute migrations:", e)
        sys.exit(1)


if __name__ == '__main__':
    main()
