"""End-to-end test: ingest a prototype repo and run analysis.

Usage:
    uv run python scripts/test_ingest_prototype.py <project_id> <repo_url> <deploy_url>

Example:
    uv run python scripts/test_ingest_prototype.py \
        859f932f-940b-40b9-8433-9a5da1166772 \
        https://github.com/33prime/v0-seton-communio-platform \
        https://v0-seton-communio-platform.vercel.app
"""

import json
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.prototypes import (
    create_prototype,
    get_prototype,
    get_prototype_for_project,
    list_overlays,
    update_prototype,
)
from app.services.bridge_injector import inject_bridge
from app.services.git_manager import GitManager

logger = get_logger(__name__)


def main():
    if len(sys.argv) < 4:
        print("Usage: uv run python scripts/test_ingest_prototype.py <project_id> <repo_url> <deploy_url>")
        sys.exit(1)

    project_id = UUID(sys.argv[1])
    repo_url = sys.argv[2]
    deploy_url = sys.argv[3]
    settings = get_settings()

    # ------------------------------------------------------------------
    # Step 1: Create or fetch prototype record
    # ------------------------------------------------------------------
    print("=" * 60)
    print("STEP 1: Create/fetch prototype record")
    print("=" * 60)

    prototype = get_prototype_for_project(project_id)
    if prototype:
        prototype_id = UUID(prototype["id"])
        print(f"  Found existing prototype: {prototype_id}")
        update_prototype(prototype_id, repo_url=repo_url, deploy_url=deploy_url, status="pending")
    else:
        prototype = create_prototype(
            project_id=project_id,
            repo_url=repo_url,
            deploy_url=deploy_url,
        )
        prototype_id = UUID(prototype["id"])
        print(f"  Created prototype: {prototype_id}")

    # ------------------------------------------------------------------
    # Step 2: Clone the repo
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STEP 2: Clone repository")
    print("=" * 60)

    git = GitManager(base_dir=settings.PROTOTYPE_TEMP_DIR)
    local_path = git.clone(repo_url, str(project_id))
    update_prototype(prototype_id, local_path=local_path)
    print(f"  Cloned to: {local_path}")

    # List the file tree
    file_tree = git.get_file_tree(local_path, extensions=[".tsx", ".ts", ".jsx", ".js"])
    print(f"  Files found: {len(file_tree)}")
    for f in file_tree[:20]:
        print(f"    {f}")
    if len(file_tree) > 20:
        print(f"    ... and {len(file_tree) - 20} more")

    # ------------------------------------------------------------------
    # Step 3: Parse HANDOFF.md
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STEP 3: Parse HANDOFF.md")
    print("=" * 60)

    handoff_parsed = {}
    try:
        handoff_content = git.read_file(local_path, "HANDOFF.md")
        handoff_parsed = {"raw": handoff_content, "features": []}
        update_prototype(prototype_id, handoff_parsed=handoff_parsed)
        print(f"  HANDOFF.md found ({len(handoff_content)} chars)")
    except FileNotFoundError:
        print("  No HANDOFF.md found (expected — v0 often skips this)")

    # ------------------------------------------------------------------
    # Step 4: Inject bridge
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STEP 4: Inject AIOS bridge")
    print("=" * 60)

    try:
        inject_bridge(git, local_path)
        print("  Bridge injected successfully")
        # Verify
        bridge_path = Path(local_path) / "public" / "aios-bridge.js"
        print(f"  Bridge script exists: {bridge_path.exists()}")
    except Exception as e:
        print(f"  Bridge injection failed: {e}")

    update_prototype(prototype_id, status="ingested")

    # ------------------------------------------------------------------
    # Step 5: Build feature-to-file mapping (heuristic)
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STEP 5: Feature-to-file mapping")
    print("=" * 60)

    from app.db.features import list_features

    features = list_features(project_id)
    print(f"  AIOS features: {len(features)}")

    # Heuristic: match feature names to component file names
    component_files = [f for f in file_tree if "components/" in f and "components/ui/" not in f]
    print(f"  Component files: {len(component_files)}")

    for feat in features:
        name = feat.get("name", "")
        name_lower = name.lower()
        matched = [f for f in component_files if any(
            word in f.lower() for word in name_lower.split() if len(word) > 3
        )]
        status = "matched" if matched else "unmatched"
        print(f"  [{status}] {name}")
        for m in matched[:2]:
            print(f"           → {m}")

    # ------------------------------------------------------------------
    # Step 6: Run analysis pipeline (optional — costs API calls)
    # ------------------------------------------------------------------
    if "--analyze" in sys.argv:
        print("\n" + "=" * 60)
        print("STEP 6: Run analysis pipeline")
        print("=" * 60)

        import uuid as uuid_mod

        from app.graphs.prototype_analysis_graph import (
            PrototypeAnalysisState,
            build_prototype_analysis_graph,
        )

        run_id = uuid_mod.uuid4()
        graph = build_prototype_analysis_graph()

        initial_state = PrototypeAnalysisState(
            prototype_id=prototype_id,
            project_id=project_id,
            run_id=run_id,
            local_path=local_path,
        )

        print(f"  Starting analysis run {run_id}...")
        final_state = graph.invoke(initial_state)

        # LangGraph returns a dict, not the dataclass
        results = final_state.get("results", []) if isinstance(final_state, dict) else final_state.results
        errors = final_state.get("errors", []) if isinstance(final_state, dict) else final_state.errors

        print(f"  Features analyzed: {len(results)}")
        print(f"  Errors: {len(errors)}")
        for r in results:
            print(f"    {r.get('feature_name')}: {r.get('status')} (confidence: {r.get('confidence', 0):.2f})")
        for e in errors:
            print(f"    ERROR: {e.get('feature')}: {e.get('error')}")

        # Check overlays in DB
        overlays = list_overlays(prototype_id)
        print(f"\n  Overlays in DB: {len(overlays)}")
    else:
        print("\n  Skipping analysis pipeline (add --analyze to run it)")
        print("  WARNING: This calls Claude for each feature and costs API credits")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    prototype = get_prototype(prototype_id)
    print(f"  Prototype ID: {prototype_id}")
    print(f"  Status: {prototype.get('status')}")
    print(f"  Deploy URL: {deploy_url}")
    print(f"  Repo URL: {repo_url}")
    print(f"  Local path: {local_path}")
    print(f"  HANDOFF found: {bool(handoff_parsed)}")
    print(f"  File count: {len(file_tree)}")


if __name__ == "__main__":
    main()
