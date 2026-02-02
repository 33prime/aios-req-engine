"""Generate a v0.dev prompt for a project and save to file.

Usage:
    uv run python scripts/generate_v0_prompt.py <project_id>
    uv run python scripts/generate_v0_prompt.py 859f932f-940b-40b9-8433-9a5da1166772
"""

import json
import sys
from pathlib import Path
from uuid import UUID

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.chains.generate_v0_prompt import build_user_message, generate_v0_prompt
from app.core.config import get_settings
from app.db.features import list_features
from app.db.personas import list_personas
from app.db.projects import get_project
from app.db.prompt_learnings import get_active_learnings
from app.db.vp import list_vp_steps


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/generate_v0_prompt.py <project_id>")
        print("\nExample:")
        print("  uv run python scripts/generate_v0_prompt.py 859f932f-940b-40b9-8433-9a5da1166772")
        sys.exit(1)

    project_id = UUID(sys.argv[1])
    settings = get_settings()

    print(f"Loading data for project {project_id}...")

    project = get_project(project_id)
    if not project:
        print(f"Project {project_id} not found")
        sys.exit(1)

    features = list_features(project_id)
    personas = list_personas(project_id)
    vp_steps = list_vp_steps(project_id)

    # Try to load learnings (table may not exist yet)
    learnings = []
    try:
        learnings = get_active_learnings()
    except Exception:
        pass

    print(f"  Project: {project.get('name')}")
    print(f"  Features: {len(features)}")
    print(f"  Personas: {len(personas)}")
    print(f"  VP Steps: {len(vp_steps)}")
    print(f"  Learnings: {len(learnings)}")

    # --- Preview mode: just build the user message (no LLM call) ---
    if "--preview" in sys.argv:
        user_msg = build_user_message(
            project=project,
            features=features,
            personas=personas,
            vp_steps=vp_steps,
            learnings=learnings if learnings else None,
        )
        out_path = Path(f"v0_input_preview_{project.get('name', 'project').replace(' ', '_')}.md")
        out_path.write_text(user_msg)
        print(f"\nPreview saved to {out_path} ({len(user_msg)} chars)")
        print("This is the raw AIOS data that gets sent to Claude for prompt generation.")
        return

    # --- Full mode: call Claude to generate the v0 prompt ---
    print(f"\nGenerating v0 prompt using {settings.PROTOTYPE_PROMPT_MODEL}...")
    result = generate_v0_prompt(
        project=project,
        features=features,
        personas=personas,
        vp_steps=vp_steps,
        settings=settings,
        learnings=learnings if learnings else None,
    )

    # Save the prompt
    safe_name = project.get("name", "project").replace(" ", "_")
    prompt_path = Path(f"v0_prompt_{safe_name}.md")
    prompt_path.write_text(result.prompt)

    # Save the full output (prompt + metadata)
    meta_path = Path(f"v0_prompt_{safe_name}_meta.json")
    meta_path.write_text(json.dumps(result.model_dump(), indent=2, default=str))

    print(f"\nv0 prompt saved to {prompt_path} ({len(result.prompt)} chars)")
    print(f"Metadata saved to {meta_path}")
    print(f"  Features included: {len(result.features_included)}")
    print(f"  Flows included: {len(result.flows_included)}")
    print(f"\nPaste the contents of {prompt_path} into v0.dev to generate the prototype.")


if __name__ == "__main__":
    main()
