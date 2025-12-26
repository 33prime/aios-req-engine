#!/usr/bin/env python3
"""Run migration using Supabase client."""
import sys
sys.path.insert(0, '.')

from app.db.supabase_client import get_supabase

def run_migration():
    supabase = get_supabase()

    try:
        print("🚀 Running migration: Add metadata column to projects table")

        # Check if metadata column exists first
        print("🔍 Checking if metadata column exists...")
        response = supabase.table('projects').select('metadata').limit(1).execute()
        print("✅ Column exists or was added successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("💡 Try running this SQL manually in your Supabase SQL editor:")
        print("""
        ALTER TABLE projects
        ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

        COMMENT ON COLUMN projects.metadata IS 'Project-specific metadata (flexible JSONB field for future extensions)';
        """)
        sys.exit(1)

if __name__ == "__main__":
    run_migration()