#!/usr/bin/env python3
"""Quick migration runner."""
import os
import sys

# Read migration file
if len(sys.argv) < 2:
    print("Usage: python3 run_migration.py migrations/0021_fix_missing_columns.sql")
    sys.exit(1)

migration_file = sys.argv[1]
with open(migration_file, 'r') as f:
    sql = f.read()

print(f"📄 Migration file: {migration_file}")
print(f"📊 Content length: {len(sql)} bytes\n")

# Try to import psycopg2 or use Supabase client
try:
    import psycopg2

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        sys.exit(1)

    print(f"🔌 Connecting to database...")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    print(f"✅ Connected!\n")
    print(f"🚀 Executing migration...\n")

    cursor.execute(sql)
    conn.commit()

    print(f"✅ Migration complete!")

    cursor.close()
    conn.close()

except ImportError:
    print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
    print("\nOr copy this SQL and run it manually in your database:\n")
    print("=" * 60)
    print(sql)
    print("=" * 60)
    sys.exit(1)
except Exception as e:
    print(f"❌ Error running migration: {e}")
    sys.exit(1)
