#!/usr/bin/env python3
"""
Validation script for Phase 1: Database Foundation

This script validates:
1. All new database modules can be imported
2. Migration files exist and are valid SQL
3. Database operation functions are available
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def validate_migrations():
    """Validate migration files exist and contain valid SQL."""
    print("✓ Validating migration files...")

    migrations_dir = project_root / "migrations"
    required_migrations = [
        "0012_enrichment_revisions.sql",
        "0013_meeting_agendas.sql",
        "0014_prd_summary_section.sql",
        "0015_features_lifecycle.sql",
    ]

    for migration_file in required_migrations:
        file_path = migrations_dir / migration_file
        if not file_path.exists():
            print(f"  ✗ Missing: {migration_file}")
            return False

        # Check file is not empty and contains SQL keywords
        content = file_path.read_text()
        if not content.strip():
            print(f"  ✗ Empty: {migration_file}")
            return False

        # Basic SQL validation
        sql_keywords = ["CREATE", "ALTER", "INSERT", "UPDATE", "SELECT"]
        if not any(keyword in content.upper() for keyword in sql_keywords):
            print(f"  ✗ Invalid SQL: {migration_file}")
            return False

        print(f"  ✓ Valid: {migration_file}")

    return True


def validate_database_modules():
    """Validate new database modules can be imported."""
    print("\n✓ Validating database modules...")

    modules_to_test = [
        ("app.db.revisions_enrichment", [
            "insert_enrichment_revision",
            "list_entity_revisions",
            "get_latest_revision",
            "count_new_signals_since",
        ]),
        ("app.db.meeting_agendas", [
            "create_meeting_agenda",
            "list_meeting_agendas",
            "get_meeting_agenda",
            "update_meeting_agenda_status",
        ]),
        ("app.db.features", [
            "update_feature_lifecycle",
            "list_features_by_lifecycle",
        ]),
        ("app.db.prd", [
            "upsert_prd_summary_section",
            "get_prd_summary_section",
        ]),
    ]

    for module_name, functions in modules_to_test:
        try:
            module = __import__(module_name, fromlist=functions)
            print(f"  ✓ Imported: {module_name}")

            # Check all required functions exist
            for func_name in functions:
                if not hasattr(module, func_name):
                    print(f"    ✗ Missing function: {func_name}")
                    return False
                print(f"    ✓ Function available: {func_name}")

        except ImportError as e:
            print(f"  ✗ Failed to import {module_name}: {e}")
            return False

    return True


def main():
    """Run all validation checks."""
    print("=" * 60)
    print("Phase 1: Database Foundation - Validation")
    print("=" * 60)

    success = True

    # Validate migrations
    if not validate_migrations():
        success = False

    # Validate database modules
    if not validate_database_modules():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("✅ All validation checks passed!")
        print("\nNext steps:")
        print("1. Apply migrations to Supabase database:")
        print("   - Use Supabase Dashboard SQL Editor")
        print("   - Or use Supabase CLI: supabase db push")
        print("2. Test the database operations with real data")
        print("3. Proceed to Phase 2: Change Logs & Context Engineering")
    else:
        print("❌ Validation failed! Please fix the issues above.")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
