# Security Scan Plan — Security Audit Agent Phase 1

Scan the codebase for security patterns, run automated Snyk scans, inventory auth/secrets/input handling, and generate an audit plan for user review.

## Arguments
$ARGUMENTS

If "quick" / "full" / "dependencies" / "auth" / "code" is provided, scope the audit.
If no arguments, default to full security audit.

## Steps

### Phase 0: Prerequisites Check

1. **Check available security tools:**
   - Snyk MCP → `snyk_code_scan`, `snyk_sca_scan`, `snyk_iac_scan`, `snyk_container_scan`
   - Supabase MCP → `execute_sql` for RLS policy audit
   - GitHub MCP → security advisories, secret scanning alerts
   - Note which are available. Missing tools mean those audit areas use codebase-only analysis.

2. **Check Snyk authentication:**
   - If Snyk MCP is available, try `snyk_auth` or `snyk_version` to confirm it's working
   - If not authenticated, guide the user through `snyk auth`

### Phase 1: Wizard Flow

3. **Audit scope** (from $ARGUMENTS or ask):
   > What kind of security audit?
   > - **Quick**: Dependency scan + secrets check + RLS coverage (~5 min)
   > - **Full**: All 4 lenses — OWASP, auth, data protection, dependencies (~20 min)
   > - **Focused**: Pick one — code / auth / data / dependencies

4. **Context:**
   > Any specific security concerns? (e.g., "preparing for SOC 2", "had a security incident", "new to Supabase RLS")
   > Is this a public-facing app or internal tool?

### Phase 2: Automated Scans

5. **Run Snyk scans** (if available, in parallel):
   - `snyk_code_scan` → SAST findings (injection, XSS, hardcoded secrets)
   - `snyk_sca_scan` → Dependency CVEs
   - `snyk_iac_scan` → Infrastructure misconfigs (if Terraform/Docker present)
   - `snyk_container_scan` → Container vulnerabilities (if Dockerfile present)

6. **Pull Supabase security state** (if available):
   ```sql
   -- RLS status
   SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';

   -- All policies
   SELECT tablename, policyname, permissive, roles, cmd, qual, with_check
   FROM pg_policies WHERE schemaname = 'public';

   -- Check for service_role usage in functions
   SELECT proname, prosecdef FROM pg_proc
   WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public');
   ```

### Phase 3: Codebase Security Scan

7. **Secrets scan:**
   - Grep for API key patterns: `sk_`, `pk_`, `api_key`, `apikey`, `secret_key`, `PRIVATE_KEY`
   - Grep for hardcoded passwords: `password\s*=\s*['"]`, `passwd`, `pwd\s*=`
   - Check if `.env` is in `.gitignore`
   - Check git history for committed secrets: `git log --all --diff-filter=A -- '*.env' '.env*'`
   - Check `.env.example` for real values vs placeholders
   - Check for `SUPABASE_SERVICE_ROLE_KEY` in any client-side/frontend code

8. **Auth pattern scan:**
   - Grep for auth middleware/decorators on route handlers
   - Identify unprotected routes (route handlers without auth checks)
   - Check JWT verification implementation
   - Check session management configuration
   - Check CORS configuration
   - Check CSRF protection

9. **Input handling scan:**
   - Grep for `dangerouslySetInnerHTML`, `innerHTML`, `v-html`
   - Grep for raw SQL queries with string concatenation
   - Grep for `eval()`, `exec()`, `child_process.exec()` with external input
   - Grep for user-controlled URLs in fetch/axios/httpx calls
   - Check input validation patterns (Zod, Pydantic, Joi schemas)

10. **Configuration scan:**
    - Check for debug mode flags in production config
    - Check error response format (does it leak stack traces?)
    - Check logging configuration (does it log sensitive data?)
    - Check CSP/HSTS/X-Frame-Options headers

### Phase 4: Generate Audit Plan

11. **Compile findings into a plan:**

    ```
    SECURITY SCAN PLAN: [Project Name]
    ═══════════════════════════════════════

    Project:     [name]
    Framework:   [detected]
    Mode:        [Quick / Full / Focused]
    Scanners:    Snyk [yes/no] | Supabase [yes/no] | GitHub [yes/no]

    ── Pre-Scan Summary ──
    Snyk Code:         [N findings] (Critical: [N], High: [N], Med: [N])
    Snyk Dependencies: [N CVEs] (Critical: [N], High: [N])
    Secrets Found:     [N] or "Clean"
    RLS Coverage:      [N]/[total] tables with RLS enabled
    Unprotected Routes:[N] route handlers without auth

    ── OWASP Lens (Code Security) ──
    - [ ] [A01] Check access control on [N] unprotected routes
    - [ ] [A03] Investigate [N] potential injection points
    - [ ] [A03] Check XSS vectors: [N] dangerouslySetInnerHTML usages
    - [ ] [A05] Review error handling for info leakage
    - [ ] [A07] Audit JWT implementation in [file]
    ...

    ── Auth Lens ──
    - [ ] Audit auth middleware coverage ([N] routes, [N] unprotected)
    - [ ] Review RLS policies on [N] client-accessed tables
    - [ ] Check session management in [file]
    - [ ] Verify CORS configuration
    ...

    ── Data Protection Lens ──
    - [ ] Investigate [N] potential hardcoded secrets
    - [ ] Check PII handling in [tables with email/phone columns]
    - [ ] Audit logging for sensitive data exposure
    - [ ] Check .env management and git history
    ...

    ── Supply Chain Lens ──
    - [ ] Review [N] critical/high CVEs from Snyk
    - [ ] Check [N] outdated dependencies
    - [ ] Verify package lock integrity
    ...

    Estimated time: [N] minutes

    Ready to execute? (y/n/adjust)
    ```

12. **Save the plan:**
    - Create `qa-reports/` directory if it doesn't exist
    - Write plan to `qa-reports/security-scan-plan-[date].md`
    - Tell the user: "Plan saved. Run `/security-audit` to execute."

## Key Principles

- **Automated first, manual second** — Run Snyk scans before grepping. Automated tools catch what grep misses.
- **Distinguish real from theoretical** — A grep match for "password" might be a test helper, not a hardcoded credential. Don't cry wolf.
- **Client vs server distinction** — A `dangerouslySetInnerHTML` in a server-rendered admin panel is less critical than in a user-facing page. Context matters.
- **Check git history** — Current code may be clean, but secrets in git history are still accessible.
- **RLS is authorization** — In Supabase apps, always check RLS alongside traditional auth middleware.
