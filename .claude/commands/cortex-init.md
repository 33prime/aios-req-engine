# Cortex Init — Bootstrap the Dynamic Memory System

Set up a self-maintaining memory file system for a project. This creates the directory structure, populates initial content by analyzing the codebase, and establishes the maintenance protocol.

## Arguments
$ARGUMENTS

If a path is provided, initialize cortex for that project directory.
If no arguments, initialize for the current working directory.

## Prerequisites

Before running this command, load the dynamic-memory skill to understand the full Cortex Protocol:
- Read `skills/practices/dynamic-memory/SKILL.md` for the philosophy, file structure, budgets, and anti-patterns

## Steps

### Phase 1: Analyze the Project

1. Determine the target project directory from $ARGUMENTS (default: cwd)
2. Scan for project identity signals:
   - `package.json` — name, description, scripts, dependencies
   - `pyproject.toml` — name, description, dependencies
   - `README.md` or `README` — project description
   - `.env.example` or `.env.local.example` — environment variables needed
   - Existing `CLAUDE.md` — any instructions already established
   - `.git/` — check `git log --oneline -20` for recent activity context
3. Scan for architecture signals:
   - Directory structure (`ls -la`, key subdirectories)
   - Framework detection (Next.js, FastAPI, Express, etc.)
   - Database detection (Supabase, Prisma, SQLAlchemy, etc.)
   - Test framework detection (vitest, pytest, jest, etc.)
   - Deployment signals (Vercel, Docker, Railway, etc.)
4. Check for existing memory:
   - Look for `~/.claude/projects/*/memory/` matching this project
   - If memory already exists, switch to **upgrade mode** (Phase 1B)

### Phase 1B: Upgrade Mode (If Memory Exists)

If a memory directory already exists:
1. Read all existing memory files
2. Assess current state against the Cortex Protocol structure
3. Identify what's missing (gotchas.md? corrections.md? health score?)
4. Identify what should be reorganized (session logs → topic files)
5. Present a migration plan to the user before making changes
6. On approval, restructure — preserving all existing knowledge, just reorganizing it

### Phase 2: Create the Memory Structure

5. Determine the memory directory path:
   - Claude Code auto-memory location: `~/.claude/projects/<project-hash>/memory/`
   - The path should match where Claude Code stores this project's memory
6. Create the topic files that don't already exist:
   - `MEMORY.md` — The index
   - `architecture.md` — System design
   - `patterns.md` — Project-specific patterns
   - `gotchas.md` — Known landmines
   - `decisions.md` — Technical choices
   - `preferences.md` — User workflow
   - `corrections.md` — Self-improvement log

### Phase 3: Populate Initial Content

7. **MEMORY.md** — Write the index:
   - Project identity from package.json/pyproject.toml/README
   - Critical constraints (empty section with prompting comment if none detected yet)
   - Active priorities (ask the user: "What are you working on right now?")
   - Quick reference (extract from package.json scripts, Makefile, or pyproject.toml)
   - Topic index with links to all topic files
   - Health score: C (initial — not yet enough data for higher)

8. **architecture.md** — Write initial architecture:
   - Data flow based on detected framework + database
   - Key directories and their purposes
   - Integration points detected from dependencies
   - Mark uncertain entries with `[inferred]` — to be confirmed

9. **patterns.md** — Seed with observed patterns:
   - Scan 3-5 representative source files for naming conventions, code organization
   - Note any patterns that deviate from framework defaults
   - Keep entries tagged with `[initial scan]` — to be refined through usage

10. **gotchas.md** — Start lean:
    - Check for common gotcha indicators: `.env.example` (environment setup), Dockerfile (build gotchas)
    - If nothing concrete is found, leave the file with a header and structure but no entries
    - Better empty than speculative — gotchas should come from real experience

11. **decisions.md** — Capture what's already decided:
    - Framework choice (from dependencies) — mark as `[inferred]` unless README explains why
    - Package manager choice (npm/pnpm/yarn/uv/pip)
    - Any decisions visible in config files (ESLint rules, TypeScript strictness, etc.)

12. **preferences.md** — Start with user interview:
    - Ask the user 3-5 quick questions:
      - "How do you prefer I communicate — concise or detailed?"
      - "Do you want me to commit changes, or just make them and let you commit?"
      - "Any tools or patterns you specifically love or hate?"
    - Store their answers
    - Mark as `[stated]` vs `[observed]` for future entries

13. **corrections.md** — Start empty:
    - Write the file header and format template
    - This file is populated through real work, never speculatively

### Phase 4: Establish the Protocol

14. If the project has a CLAUDE.md, suggest adding a Cortex Protocol section:
    ```markdown
    ## Memory Protocol
    This project uses the Cortex Protocol for persistent memory management.
    - Memory files: ~/.claude/projects/<path>/memory/
    - Maintain memory after every significant task
    - Run `/cortex-optimize` when health score drops below B
    - Your memory is the single most important artifact you maintain
    ```
    Show the user the proposed addition and ask for approval before writing.

15. If no CLAUDE.md exists, suggest creating a minimal one with the protocol section plus basic project context.

### Phase 5: Report

16. Display a summary:
    ```
    Cortex Initialized
    ==================
    Project: [name]
    Memory: [path]
    Files created: [list]

    Initial Health Score: C
    (Score will improve as you work on the project and maintain memory)

    Topic Files:
      MEMORY.md      — [N] lines (budget: 150)
      architecture.md — [N] lines (budget: 200)
      patterns.md     — [N] lines (budget: 150)
      gotchas.md      — [N] lines (budget: 100)
      decisions.md    — [N] lines (budget: 150)
      preferences.md  — [N] lines (budget: 100)
      corrections.md  — [N] lines (budget: 100)

    Next steps:
    1. Work on your project normally
    2. Memory will update as you work
    3. Run /cortex-optimize periodically to prune and score
    ```

## Key Principles

- **Analyze first, write second** — understand the project before creating memory
- **Never speculate** — if you're not sure about something, leave it empty or mark it `[inferred]`
- **Ask the user** — preferences and priorities come from the human, not from guessing
- **Respect existing work** — if memory files exist, upgrade them, don't overwrite
- **Under-fill, don't over-fill** — a sparse but accurate memory is better than a bloated speculative one
- **The memory is for Claude, not for humans** — write in the way that will be most useful for future Claude sessions, not in a way that reads like documentation
