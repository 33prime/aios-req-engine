#!/usr/bin/env python3
"""
Weekly architecture documentation updater.

This script is designed to be run by Claude Cowork every Friday to:
1. Scan the codebase for changes
2. Update architecture docs
3. Add changelog entry
4. Commit changes

Usage:
    python update_architecture_docs.py
"""

import subprocess
from datetime import datetime
from pathlib import Path

# Root directory
REPO_ROOT = Path(__file__).parent.parent
DOCS_DIR = REPO_ROOT / "docs" / "architecture"

def get_git_changes_this_week():
    """Get git commit messages from the last 7 days."""
    result = subprocess.run(
        ["git", "log", "--since=7.days", "--pretty=format:%s"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT
    )
    return result.stdout.strip().split('\n') if result.stdout else []

def scan_api_endpoints():
    """Scan app/api/ for new or modified endpoints."""
    api_dir = REPO_ROOT / "app" / "api"
    endpoints = []
    
    for py_file in api_dir.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
        # TODO: Parse router definitions to extract endpoints
        endpoints.append(py_file.stem)
    
    return endpoints

def scan_database_tables():
    """Scan app/db/ for database tables."""
    db_dir = REPO_ROOT / "app" / "db"
    tables = []
    
    for py_file in db_dir.glob("*.py"):
        if py_file.name.startswith("__") or py_file.name == "supabase_client.py":
            continue
        tables.append(py_file.stem)
    
    return tables

def scan_agents():
    """Scan app/agents/ for LangGraph agents."""
    agents_dir = REPO_ROOT / "app" / "agents"
    agents = []
    
    for py_file in agents_dir.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        agents.append(py_file.stem)
    
    return agents

def update_changelog(week_summary: str):
    """Add weekly entry to changelog."""
    changelog_path = DOCS_DIR / "changelog.md"
    
    # Read existing changelog
    with open(changelog_path, 'r') as f:
        content = f.read()
    
    # Generate new entry
    now = datetime.now()
    week_start = now.strftime("%B %d")
    week_end = (now).strftime("%B %d, %Y")
    
    new_entry = f"""
## Week of {week_start} - {week_end}

### Major Changes

{week_summary}

### Breaking Changes
- None this week

### Deprecations
- None this week

---

"""
    
    # Insert after header
    lines = content.split('\n')
    header_end = 0
    for i, line in enumerate(lines):
        if line.startswith('---') and i > 5:  # Find first --- after header
            header_end = i + 1
            break
    
    updated_lines = lines[:header_end] + new_entry.split('\n') + lines[header_end:]
    
    # Write updated changelog
    with open(changelog_path, 'w') as f:
        f.write('\n'.join(updated_lines))
    
    print(f"✓ Updated changelog.md with week of {week_start}")

def generate_weekly_summary():
    """Generate summary of changes this week."""
    commits = get_git_changes_this_week()
    
    # Group commits by category
    features = [c for c in commits if c.lower().startswith('feat')]
    fixes = [c for c in commits if c.lower().startswith('fix')]
    docs = [c for c in commits if c.lower().startswith('docs')]
    
    summary = []
    
    if features:
        summary.append("**New Features**")
        for feat in features[:5]:  # Top 5
            summary.append(f"- {feat.replace('feat:', '').strip()}")
    
    if fixes:
        summary.append("\n**Bug Fixes**")
        for fix in fixes[:5]:
            summary.append(f"- {fix.replace('fix:', '').strip()}")
    
    if docs:
        summary.append("\n**Documentation**")
        for doc in docs[:3]:
            summary.append(f"- {doc.replace('docs:', '').strip()}")
    
    if not summary:
        summary.append("**Maintenance**")
        summary.append("- Minor updates and bug fixes")
    
    return '\n'.join(summary)

def update_stats():
    """Update statistics in overview.md."""
    # Count endpoints
    api_count = len(scan_api_endpoints())
    
    # Count tables
    table_count = len(scan_database_tables())
    
    # Count agents
    agent_count = len(scan_agents())
    
    print(f"✓ Found {api_count} API modules, {table_count} DB tables, {agent_count} agents")
    
    # TODO: Update overview.md with these counts

def main():
    """Main update routine."""
    print("AIOS Req Engine - Weekly Architecture Doc Update")
    print("=" * 60)
    print()
    
    # 1. Scan codebase
    print("📊 Scanning codebase...")
    endpoints = scan_api_endpoints()
    tables = scan_database_tables()
    agents = scan_agents()
    print(f"   Found: {len(endpoints)} API modules, {len(tables)} tables, {len(agents)} agents")
    print()
    
    # 2. Generate summary
    print("📝 Generating weekly summary...")
    summary = generate_weekly_summary()
    print(summary)
    print()
    
    # 3. Update changelog
    print("📋 Updating changelog...")
    update_changelog(summary)
    print()
    
    # 4. Update stats (TODO)
    print("📈 Updating statistics...")
    update_stats()
    print()
    
    print("✅ Architecture docs updated!")
    print()
    print("Next steps:")
    print("1. Review the updated docs in docs/architecture/")
    print("2. Make any manual adjustments if needed")
    print("3. Commit with: git commit -m 'docs: weekly architecture update'")

if __name__ == "__main__":
    main()
