# Integrate Forge Module

Install a module from rtg-forge into the current project.

## Steps
1. Read module's MODULE.md for setup instructions
2. Read module.toml for dependencies and config requirements
3. Copy module directory into project's modules/ directory
4. Install Python dependencies listed in module.toml
5. Add required env vars to .env (from config.py)
6. Run SQL migrations from module's migrations/ directory
7. Mount the router in main.py
8. Run module's tests to verify integration
9. Report any issues

## Arguments
Module name: $ARGUMENTS
