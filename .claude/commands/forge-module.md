# Forge Module — The Module Agent

The forge's hands. Scout extractable patterns, extract them as modules, match forge modules to project needs, or install them with personalization. One agent, four capabilities — the wizard determines which fire.

## Arguments
$ARGUMENTS

**Scope keywords** (determines which capabilities run):
- `scout` or `scan` → Scout only: find extractable patterns in this codebase
- `extract [path/pattern]` → Extract: pull a specific pattern into forge module format
- `match [need]` or `find [need]` → Match: search forge for modules that fit a need
- `install [module_name]` → Install: personalize and integrate a specific module
- `setup` or `new project` → Match + Install loop: recommend and install multiple modules
- No arguments → Wizard asks what you need

## Steps

### Phase 0: Wizard — Determine Scope

1. **Parse $ARGUMENTS** for scope keywords. If none provided, ask:
   > What do you need?
   > - **Scout** — Find extractable patterns in this codebase
   > - **Extract** — Extract a specific pattern as a forge module
   > - **Match** — Find a forge module for a specific need
   > - **Install** — Install a specific forge module in this project
   > - **Setup** — Full new project setup (match + install loop)

2. **Set active phases** based on scope:
   | Scope | Phases |
   |-------|--------|
   | Scout | Scout only |
   | Extract | Extract only (or Scout → Extract if target unclear) |
   | Match | Match only |
   | Install | Install only |
   | Setup | Match → Install (loop) |

---

### Phase 1: Scout (if active)

**Goal**: Find patterns worth extracting from the current codebase.

3. **Scan project structure**:
   - Identify feature directories (own router + service + models)
   - Look for self-contained integrations (external API wrappers, pipelines)
   - Look for reusable business logic (not just CRUD)
   - Check for service layers with significant logic

4. **For each candidate, evaluate**:
   - **Pattern Detective**: Is the boundary clean? Self-contained? Deletable without breaking the app?
   - **Architecture Critic**: Layer separation? Config management? Error handling? Testability?
   - **Decision Mapper**: What's hardcoded that other projects would change?

5. **Check forge for duplicates**:
   - Call `search_modules` with candidate keywords
   - If similar module exists: note "Similar to forge module [name] — consider contributing improvements instead of extracting a new one"

6. **Score and present candidates** (see AGENT.md for format)

7. **Confirmation gate**: User approves candidates to extract (or stops here if just scouting).

---

### Phase 2: Extract (if active)

**Goal**: Pull an approved pattern into forge module format.

8. **Identify the target**:
   - From $ARGUMENTS: specific directory or pattern name
   - From Scout results: approved candidate
   - If unclear: ask "Which directory or feature should I extract?"

9. **Read all source files** in the target directory

10. **Build module.toml**:
    - Populate `[module]` metadata
    - List `[module.dependencies]` from imports and requirements
    - Define `[module.api]` from route decorators
    - List `[module.database]` from migrations or queries
    - Build `[ai]` section: tags, use_when, complexity
    - **For each decision the Decision Mapper identifies**:
      - Create `[[ai.decisions.required]]` with key, label, question, options, default
      - Determine stage (discovery, solution_flow, implementation)
      - Determine impact (architecture, naming, feature_scope)
    - Declare frontend manifests: `[[ai.companions.frontend_views]]`, `.frontend_components`, `.frontend_hooks`
    - Build `[enforcement]` rules from the Architecture Critic's assessment

11. **Write MODULE.md**: What, why, architecture, decisions guide, setup, API reference

12. **Clean source files**:
    - Replace hardcoded values with config references
    - Ensure router → service → models layer discipline
    - Ensure service is framework-agnostic
    - Add type hints and docstrings to public functions

13. **Create the module directory** in the forge:
    ```
    modules/{name}/
    ├── module.toml
    ├── MODULE.md
    ├── __init__.py
    ├── router.py
    ├── service.py
    ├── models.py
    ├── config.py
    └── migrations/
        └── 001_create_tables.sql
    ```

14. **Validate**: Call `validate_module` MCP tool

15. **Score and report** (see AGENT.md for format)

16. **Confirmation gate**: User reviews the extracted module.

---

### Phase 3: Match (if active)

**Goal**: Find the best forge module(s) for a stated need.

17. **Understand the project**:
    - Read CLAUDE.md, package.json / pyproject.toml
    - Check `.forge/manifest.toml` for already-installed modules
    - Identify tech stack (framework, database, auth)

18. **Understand the need**:
    - From $ARGUMENTS: the stated need
    - If unclear: ask "What are you trying to build or solve?"

19. **Search the forge**:
    - Call `search_modules` with need keywords
    - Call `list_modules` for full catalog
    - For each candidate: call `get_module` to read module.toml

20. **Rank by fit** (see AGENT.md scoring matrix)

21. **Present recommendations** with fit percentages and rationale

22. **Confirmation gate**:
    - "Want to install one of these?" (number / no / tell me more)
    - If yes: proceed to Install phase with selected module
    - If "setup" mode: loop — after installing one, ask "Next recommendation?"

---

### Phase 4: Install (if active)

**Goal**: Personalize a forge module and integrate it into this project.

23. **Load the module**:
    - Call `get_module` for module.toml + MODULE.md
    - Call `get_module_sources` for all source files
    - Call `get_module_setup` for setup requirements

24. **Read the target project** (if not already done in Match):
    - Architecture, conventions, naming, auth pattern, database conventions
    - Existing dependencies, directory structure

25. **Personalization interview**:
    For each `[[ai.decisions.required]]` in module.toml:
    - Ask the question with context from the target project
    - Explain options with pros/cons relevant to this project
    - Record the choice

    Additional questions:
    - Entity naming adaptation
    - Integration with existing tables/services
    - Field additions/removals
    - Auth integration approach

26. **Adapt the code** (Integration Architect lens):
    - Rename entities throughout
    - Adjust models for the domain
    - Modify service logic for the use case
    - Update migrations with correct names
    - Wire into existing patterns (auth, error handling, config)
    - Follow the project's conventions

27. **Install**:
    - Create directory in target project
    - Write adapted files
    - Install dependencies
    - Add env vars
    - Mount router
    - Run migrations
    - Run tests

28. **Verify** (Architecture Critic lens):
    - Run module enforcement rules against adapted code
    - Check layer rules, config patterns, error handling

29. **Record**:
    - Update `.forge/manifest.toml`
    - Call `record_module_usage` MCP tool with full details:
      - module_name, project_name, use_case
      - decisions made, adaptations applied
      - estimated_hours_saved
      - missing_decisions (if any decision was needed but not in module.toml)
    - Optional: Slack notification to #forge

30. **Report** (see AGENT.md for format)

---

### Phase 5: Post-Install (Setup mode only)

31. **If running in Setup mode**:
    - After installing a module, check if it has companion modules
    - Ask: "This module pairs well with [companion]. Want to install it too?"
    - Loop back to Install phase for each approved companion
    - When done, present the full setup summary:
      ```
      PROJECT SETUP COMPLETE
      ══════════════════════

      Modules Installed: [N]
        1. [module] — [use case] — [decisions made]
        2. [module] — [use case] — [decisions made]

      Total Decisions Made: [N]
      Total Files Created:  [N]
      Env Vars Required:    [list]

      Next Steps:
        1. Set env vars
        2. Run all migrations
        3. Run test suite
      ```

## Key Principles

- **One question determines scope** — Don't run four capabilities when the user needs one.
- **Each phase has a gate** — User can stop after Scout, after Extract, after Match. Never force the full pipeline.
- **Personalization is the value** — A blind install is a copy-paste. The interview IS the product.
- **Record everything** — Usage data makes the forge smarter. Missing decisions evolve modules.
- **Check for duplicates first** — Before extracting, search the forge. Before installing, check the manifest.
- **Backend only** — Frontend surfaces are declared as manifests, not extracted as code.
