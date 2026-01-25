"""
Manually trigger signal processing for a project.

Run with: uv run python scripts/manual_process_signals.py <project_id>
"""

import asyncio
import sys
from uuid import UUID, uuid4

from app.core.signal_pipeline import process_signal
from app.db.supabase_client import get_supabase


async def process_all_signals(project_id: UUID):
    """Process all unprocessed signals for a project."""
    supabase = get_supabase()

    # Get all signals for project
    result = supabase.table("signals").select("*").eq("project_id", str(project_id)).execute()
    signals = result.data or []

    print(f"Found {len(signals)} signals for project {project_id}")

    for signal in signals:
        signal_id = UUID(signal["id"])
        content = signal.get("content", "")
        signal_type = signal.get("signal_type", "signal")
        title = signal.get("title", "Untitled")

        print(f"\nProcessing signal: {title} ({signal_id})")
        print(f"  Type: {signal_type}")
        print(f"  Content length: {len(content)} chars")

        try:
            run_id = uuid4()
            result = await process_signal(
                project_id=project_id,
                signal_id=signal_id,
                run_id=run_id,
                signal_content=content,
                signal_type=signal_type,
                signal_metadata={"title": title},
            )

            print(f"  ✓ Success: {result.get('pipeline')} pipeline")
            print(f"    - Features: {result.get('features_created', 0)} created")
            print(f"    - Personas: {result.get('personas_created', 0)} created")
            print(f"    - VP Steps: {result.get('vp_steps_created', 0)} created")
            if result.get('proposal_id'):
                print(f"    - Proposal: {result['proposal_id']}")

        except Exception as e:
            print(f"  ✗ Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/manual_process_signals.py <project_id>")
        sys.exit(1)

    project_id = UUID(sys.argv[1])
    asyncio.run(process_all_signals(project_id))
