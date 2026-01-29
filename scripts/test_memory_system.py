#!/usr/bin/env python3
"""
Memory System End-to-End Test Script

This script tests the memory knowledge graph system by:
1. Creating a test project (or using existing)
2. Simulating signal events through the memory watcher
3. Verifying beliefs are created and evolve
4. Running reflection to generate insights
5. Rendering the final markdown view

Usage:
    # With test mode (uses mock LLM responses)
    uv run python scripts/test_memory_system.py --test-mode

    # Against real API (requires ANTHROPIC_API_KEY)
    uv run python scripts/test_memory_system.py --project-id <uuid>

    # Create new test project
    uv run python scripts/test_memory_system.py --create-project
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Mock Responses for Test Mode
# =============================================================================

MOCK_WATCHER_RESPONSES = [
    {
        "facts": [
            {"content": "CTO Sarah mentioned Q2 compliance deadline in kickoff email", "summary": "Q2 compliance deadline mentioned"}
        ],
        "importance": 0.75,
        "contradicts_beliefs": [],
        "confirms_beliefs": [],
        "is_milestone": False,
        "rationale": "New important deadline information"
    },
    {
        "facts": [
            {"content": "CEO stated mobile-first is top priority during board meeting", "summary": "Mobile-first stated priority"}
        ],
        "importance": 0.8,
        "contradicts_beliefs": [],
        "confirms_beliefs": [],
        "is_milestone": False,
        "rationale": "Strategic priority from leadership"
    },
    {
        "facts": [
            {"content": "Budget allocated 70% to compliance features, 20% to mobile", "summary": "Budget: 70% compliance, 20% mobile"}
        ],
        "importance": 0.85,
        "contradicts_beliefs": ["Mobile-first stated priority"],
        "confirms_beliefs": ["Q2 compliance deadline"],
        "is_milestone": True,
        "rationale": "Budget allocation contradicts stated mobile priority"
    },
]

MOCK_SYNTHESIZER_RESPONSES = [
    [
        {"action": "create_belief", "content": "Q2 compliance deadline is driving immediate priorities", "summary": "Q2 compliance driving priorities", "confidence": 0.7, "domain": "client_priority", "supported_by": []}
    ],
    [
        {"action": "create_belief", "content": "Leadership says mobile-first but this may not reflect actual priorities", "summary": "Mobile-first stated but uncertain", "confidence": 0.6, "domain": "client_priority", "supported_by": []}
    ],
    [
        {"action": "update_belief_confidence", "belief_id": "PLACEHOLDER", "new_confidence": 0.85, "reason": "Budget allocation confirms compliance priority"},
        {"action": "update_belief_confidence", "belief_id": "PLACEHOLDER", "new_confidence": 0.4, "reason": "Budget contradicts mobile priority claim"},
        {"action": "create_belief", "content": "Client's stated priorities (mobile) differ from actual resource allocation (compliance)", "summary": "Stated vs actual priority mismatch", "confidence": 0.8, "domain": "client_priority", "supported_by": []}
    ],
]

MOCK_REFLECTOR_RESPONSE = {
    "insights": [
        {
            "content": "Pattern detected: Leadership communicates aspirational priorities (mobile-first) while resource allocation reveals operational priorities (compliance). This suggests either miscommunication or deliberate prioritization that contradicts public statements.",
            "summary": "Aspirational vs operational priority disconnect",
            "confidence": 0.75,
            "type": "behavioral",
            "supported_by": []
        },
        {
            "content": "Risk identified: If team builds for mobile-first while resources go to compliance, there will be delivery conflicts. Recommend clarifying true priorities with stakeholders.",
            "summary": "Mobile vs compliance delivery risk",
            "confidence": 0.7,
            "type": "risk",
            "supported_by": []
        }
    ]
}


# =============================================================================
# Test Scenarios
# =============================================================================

TEST_SIGNALS = [
    {
        "type": "email",
        "content": """
        From: Sarah Chen (CTO)
        Subject: Q2 Compliance Deadline

        Team,

        Just a reminder that we have a hard compliance deadline in Q2.
        The audit team will be reviewing our systems in April.
        This is non-negotiable - we need all compliance features ready.

        Sarah
        """,
        "entities": {"features_created": 2, "stakeholders_found": 1}
    },
    {
        "type": "meeting_notes",
        "content": """
        Board Meeting Notes - January 2025

        Key Points:
        - CEO emphasized mobile-first strategy
        - "Our users are mobile-first, we need to be too"
        - Goal: 50% of transactions via mobile by Q3
        - Mobile app redesign approved

        Attendees: CEO, CFO, CTO, Board Members
        """,
        "entities": {"personas_found": 1, "features_created": 3}
    },
    {
        "type": "budget_report",
        "content": """
        Q1-Q2 Development Budget Allocation

        - Compliance Features: $350,000 (70%)
        - Mobile Development: $100,000 (20%)
        - Infrastructure: $50,000 (10%)

        Note: Compliance allocation increased due to regulatory requirements.
        Mobile budget reduced from initial projections.
        """,
        "entities": {"business_drivers_created": 2}
    },
]


# =============================================================================
# Main Test Flow
# =============================================================================

async def run_test(
    project_id: UUID,
    test_mode: bool = False,
    verbose: bool = True,
):
    """Run the full memory system test."""

    print("\n" + "=" * 60)
    print("MEMORY SYSTEM END-TO-END TEST")
    print("=" * 60)
    print(f"Project ID: {project_id}")
    print(f"Test Mode: {test_mode}")
    print(f"Started: {datetime.utcnow().isoformat()}")
    print("=" * 60 + "\n")

    results = {
        "signals_processed": 0,
        "facts_created": 0,
        "beliefs_created": 0,
        "beliefs_updated": 0,
        "insights_created": 0,
        "errors": [],
    }

    if test_mode:
        # Use mock responses
        await run_test_mode(project_id, results, verbose)
    else:
        # Use real API
        await run_live_mode(project_id, results, verbose)

    # Print summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Signals Processed: {results['signals_processed']}")
    print(f"Facts Created: {results['facts_created']}")
    print(f"Beliefs Created: {results['beliefs_created']}")
    print(f"Beliefs Updated: {results['beliefs_updated']}")
    print(f"Insights Created: {results['insights_created']}")
    print(f"Errors: {len(results['errors'])}")

    if results['errors']:
        print("\nErrors encountered:")
        for err in results['errors']:
            print(f"  - {err}")

    print("=" * 60 + "\n")

    return results


async def run_test_mode(project_id: UUID, results: dict, verbose: bool):
    """Run test with mock responses (no API calls)."""
    from unittest.mock import MagicMock, patch
    import json

    print("\n[TEST MODE] Using mock LLM responses\n")

    # Track created beliefs for updating
    created_beliefs = []

    for i, signal in enumerate(TEST_SIGNALS):
        print(f"\n--- Signal {i+1}/{len(TEST_SIGNALS)}: {signal['type']} ---")
        if verbose:
            print(f"Content preview: {signal['content'][:100]}...")

        # Mock the watcher
        watcher_response = MOCK_WATCHER_RESPONSES[i]
        print(f"[Watcher] Extracted {len(watcher_response['facts'])} facts, importance: {watcher_response['importance']}")

        for fact in watcher_response['facts']:
            print(f"  - Fact: {fact['summary']}")
            results['facts_created'] += 1

        if watcher_response['contradicts_beliefs']:
            print(f"  - Contradicts: {watcher_response['contradicts_beliefs']}")
        if watcher_response['confirms_beliefs']:
            print(f"  - Confirms: {watcher_response['confirms_beliefs']}")

        # Mock the synthesizer if triggered
        if watcher_response['importance'] >= 0.7 or watcher_response['contradicts_beliefs']:
            print(f"[Synthesizer] Triggered (importance={watcher_response['importance']}, contradictions={len(watcher_response['contradicts_beliefs'])})")

            synth_response = MOCK_SYNTHESIZER_RESPONSES[i]
            for action in synth_response:
                if action['action'] == 'create_belief':
                    print(f"  - Created belief: {action['summary']} (conf: {action['confidence']})")
                    created_beliefs.append({'id': str(uuid4()), 'summary': action['summary']})
                    results['beliefs_created'] += 1
                elif action['action'] == 'update_belief_confidence':
                    print(f"  - Updated belief confidence to {action['new_confidence']}: {action['reason'][:50]}...")
                    results['beliefs_updated'] += 1

        results['signals_processed'] += 1

    # Run reflection
    print(f"\n--- Running Reflection ---")
    reflect_response = MOCK_REFLECTOR_RESPONSE
    for insight in reflect_response['insights']:
        print(f"  - Insight ({insight['type']}): {insight['summary']}")
        results['insights_created'] += 1

    # Show final markdown (mock)
    print(f"\n--- Rendered Memory Document ---\n")
    print(generate_mock_markdown(created_beliefs, reflect_response['insights']))


async def run_live_mode(project_id: UUID, results: dict, verbose: bool):
    """Run test with real API calls."""
    from app.agents.memory_agent import (
        MemoryWatcher,
        MemorySynthesizer,
        MemoryReflector,
        process_signal_for_memory,
    )
    from app.core.memory_renderer import render_memory_markdown
    from app.db.memory_graph import get_active_beliefs, get_insights, get_graph_stats

    print("\n[LIVE MODE] Using real API calls\n")

    watcher = MemoryWatcher()
    synthesizer = MemorySynthesizer()
    reflector = MemoryReflector()

    for i, signal in enumerate(TEST_SIGNALS):
        print(f"\n--- Signal {i+1}/{len(TEST_SIGNALS)}: {signal['type']} ---")

        try:
            result = await process_signal_for_memory(
                project_id=project_id,
                signal_id=uuid4(),
                signal_type=signal['type'],
                raw_text=signal['content'],
                entities_extracted=signal['entities'],
            )

            print(f"[Watcher] Extracted {len(result.get('facts', []))} facts")
            print(f"[Watcher] Importance: {result.get('importance', 0)}")

            for fact in result.get('facts', []):
                print(f"  - Fact: {fact.get('summary', 'N/A')}")
                results['facts_created'] += 1

            if result.get('triggers_synthesis'):
                print(f"[Synthesizer] Triggered")
                if 'synthesis_result' in result:
                    sr = result['synthesis_result']
                    results['beliefs_created'] += sr.get('beliefs_created', 0)
                    results['beliefs_updated'] += sr.get('beliefs_updated', 0)
                    print(f"  - Beliefs created: {sr.get('beliefs_created', 0)}")
                    print(f"  - Beliefs updated: {sr.get('beliefs_updated', 0)}")

            results['signals_processed'] += 1

        except Exception as e:
            print(f"[ERROR] {e}")
            results['errors'].append(f"Signal {i+1}: {str(e)}")

        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)

    # Run reflection
    print(f"\n--- Running Reflection ---")
    try:
        reflect_result = await reflector.reflect(project_id)
        results['insights_created'] += reflect_result.get('insights_created', 0)
        print(f"[Reflector] Created {reflect_result.get('insights_created', 0)} insights")
        for insight in reflect_result.get('insights', []):
            print(f"  - {insight.get('type', 'unknown')}: {insight.get('summary', 'N/A')}")
    except Exception as e:
        print(f"[ERROR] Reflection failed: {e}")
        results['errors'].append(f"Reflection: {str(e)}")

    # Show graph stats
    print(f"\n--- Graph Statistics ---")
    try:
        stats = get_graph_stats(project_id)
        print(f"  Facts: {stats.get('facts_count', 0)}")
        print(f"  Beliefs: {stats.get('beliefs_count', 0)}")
        print(f"  Insights: {stats.get('insights_count', 0)}")
        print(f"  Edges: {stats.get('total_edges', 0)}")
        print(f"  Avg belief confidence: {stats.get('average_belief_confidence', 0):.0%}")
    except Exception as e:
        print(f"  [Could not retrieve stats: {e}]")

    # Render final markdown
    print(f"\n--- Rendered Memory Document ---\n")
    try:
        markdown = await render_memory_markdown(project_id)
        print(markdown)
    except Exception as e:
        print(f"[ERROR] Could not render markdown: {e}")
        results['errors'].append(f"Render: {str(e)}")


def generate_mock_markdown(beliefs: list, insights: list) -> str:
    """Generate mock markdown for test mode."""
    lines = [
        "# Project Memory: Test Project",
        f"*Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC*\n",
        "## Current Understanding\n",
    ]

    for b in beliefs:
        lines.append(f"**[████░]** {b['summary']}")

    lines.append("\n## Strategic Insights\n")
    for i in insights:
        emoji = {"behavioral": "👤", "risk": "⚠️"}.get(i['type'], "📌")
        lines.append(f"### {emoji} {i['summary']}\n")
        lines.append(i['content'])
        lines.append("")

    lines.append("## Recent Observations\n")
    lines.append("- [2025-01-15] Q2 compliance deadline mentioned")
    lines.append("- [2025-01-16] Mobile-first stated priority")
    lines.append("- [2025-01-17] Budget: 70% compliance, 20% mobile")

    return "\n".join(lines)


# =============================================================================
# Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Test the Memory Knowledge Graph System")
    parser.add_argument(
        "--project-id",
        type=str,
        help="Project UUID to test against (creates test project if not specified)"
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Use mock responses (no API calls)"
    )
    parser.add_argument(
        "--create-project",
        action="store_true",
        help="Create a new test project"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Get or create project ID
    if args.project_id:
        project_id = UUID(args.project_id)
    elif args.create_project and not args.test_mode:
        # Would create a real project here
        print("Creating test project requires database connection.")
        print("Use --test-mode for mock testing, or provide --project-id")
        return 1
    else:
        # Use a random UUID for test mode
        project_id = uuid4()

    # Run the test
    asyncio.run(run_test(
        project_id=project_id,
        test_mode=args.test_mode,
        verbose=args.verbose,
    ))

    return 0


if __name__ == "__main__":
    sys.exit(main())
