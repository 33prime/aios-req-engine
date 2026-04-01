# Security Audit — Security Audit Agent Phase 2

Execute an approved security scan plan. Cross-reference findings across four expert lenses, assess exploitability, score security posture, and produce a prioritized report with remediations.

## Arguments
$ARGUMENTS

If a project name is provided, look for its scan plan in `qa-reports/`.
If no arguments, check `qa-reports/` for the most recent security-scan-plan and confirm with the user.
If no plan exists, run the wizard flow inline (combined Phase 1 + Phase 2).

## Steps

### Phase 0: Load Scan Plan

1. **Find the plan:**
   - Search `qa-reports/` for `security-scan-plan-*.md` files
   - If multiple, use the most recent
   - If none found: offer to generate and execute in one pass

2. **Confirm with user:**
   > Ready to execute security audit on [project] in [Quick/Full] mode.
   > Pre-scan found: [N] Snyk findings, [N] secrets concerns, [N] RLS gaps
   > Proceed? (y/n)

### Phase 1: OWASP Analysis (OWASP Analyst Lens)

3. **For each potential vulnerability from the scan plan:**

   a. **Read the actual code** — Don't just rely on the grep match. Read 20 lines of context.
   b. **Determine exploitability:**
      - Is the vulnerable code reachable from external input?
      - Is there any sanitization/validation upstream?
      - What's the blast radius if exploited? (data loss, unauthorized access, code execution)
   c. **Classify:**
      - Confirmed: Definitely exploitable
      - Likely: Exploitable under certain conditions
      - Potential: Theoretically vulnerable but mitigated by other controls
      - False positive: Grep match but not actually vulnerable

4. **For each Snyk code finding:**
   - Read the flagged code
   - Assess whether it's actually reachable
   - If reachable: write the exploit scenario
   - If not reachable: note as "mitigated" with explanation

5. **Check OWASP categories not covered by automated scans:**
   - Broken access control: Read route handlers, check for auth middleware
   - Security misconfiguration: Check error responses, debug flags
   - SSRF: Check for user-controlled URLs in backend HTTP calls

### Phase 2: Auth & Authorization Analysis (Auth Architect Lens)

6. **Route protection audit:**
   - For each API route handler:
     - Is there auth middleware?
     - If protected: what level? (authenticated, admin, owner)
     - If unprotected: is it intentionally public?
   - Map the result:
     ```
     Route Protection Matrix:
     /api/users          → auth required ✓
     /api/admin/stats    → admin required ✓
     /api/webhooks/stripe → signature verification ✓
     /api/health         → public (intentional) ✓
     /api/export/data    → NO AUTH ← FINDING
     ```

7. **RLS deep dive** (if Supabase available):
   - For each client-accessed table (from codebase grep):
     - Is RLS enabled?
     - Do policies cover all operations the client uses?
     - Does the policy logic match the access pattern?
     - Test with a specific scenario:
       ```sql
       -- Simulate: Can user A see user B's data?
       -- (construct query based on actual client query, but with wrong user_id)
       SELECT COUNT(*) FROM [table] WHERE user_id != '[test_user_id]';
       -- If RLS works, this should return 0 from the client's perspective
       ```

8. **JWT/Session analysis:**
   - Read the JWT configuration/verification code
   - Check: signing algorithm (RS256 preferred over HS256)
   - Check: token expiry (not too long, not too short)
   - Check: token storage (httpOnly cookie > localStorage)
   - Check: refresh token rotation
   - Check: session invalidation on password change

9. **CORS analysis:**
   - Read the CORS configuration
   - Check: origins are specific (not `*` in production)
   - Check: credentials flag alignment with origin
   - Check: methods are limited to what's needed

### Phase 3: Data Protection Analysis (Data Protection Officer Lens)

10. **Secrets verification:**
    - For each potential secret found in Phase 1:
      - Read the file in context
      - Determine if it's a real secret or a test/placeholder
      - Check if it's in `.gitignore`
      - Check git history: `git log --all -p -S '[secret pattern]' -- [file]`
    - For service role key specifically:
      - Grep ALL frontend/client code for `SERVICE_ROLE`
      - If found: **Critical** — this bypasses all RLS

11. **PII inventory:**
    - From the schema (or codebase models), identify PII columns:
      - email, phone, address, date_of_birth, ip_address
      - payment info, government IDs
    - For each PII field:
      - Is it returned in API responses? (grep for the column name in response models)
      - Is it logged? (grep for the column name near logger calls)
      - Is it included in analytics/tracking events?

12. **Logging hygiene:**
    - Grep for logger/console calls that include:
      - Request bodies (may contain passwords)
      - Headers (may contain tokens)
      - User data (may contain PII)
    - Check error handlers: do they log full error objects with request data?

### Phase 4: Supply Chain Analysis (Supply Chain Auditor Lens)

13. **CVE triage** (from Snyk scan or manual check):
    - For each Critical/High CVE:
      - Is the vulnerable function actually imported?
      - Is the vulnerable code path reachable from this application?
      - Is there a fixed version available?
      - What's the upgrade path? (breaking changes?)
    - Prioritize by: exploitability > severity > fix availability

14. **Dependency health:**
    - Count dependencies by age:
      - How many are >1 major version behind?
      - How many had their last publish >2 years ago?
    - Check for known problematic patterns:
      - Deprecated packages still in use
      - Packages with known supply chain incidents
    - Check lock file integrity:
      - Does `package-lock.json` / `uv.lock` exist?
      - Are there dependencies not pinned?

### Phase 5: Cross-Reference and Score

15. **Cross-reference findings across lenses:**
    - Auth finding + RLS finding on same table → compound risk
    - Dependency CVE + code pattern using vulnerable function → confirmed exploitable
    - Secret in git history + no key rotation → active exposure
    - Unprotected route + no RLS on accessed table → critical path

16. **Calculate Security Posture Score:**

    **Code Security (0–100, weight 30%):**
    - Start at 100
    - -20 per confirmed Critical vulnerability
    - -10 per confirmed High vulnerability
    - -5 per confirmed Medium vulnerability
    - -5 per unprotected route accessing sensitive data

    **Auth & Access (0–100, weight 25%):**
    - Start at 100
    - -25 per client-accessed table without RLS
    - -15 per missing auth middleware on sensitive route
    - -10 per CORS misconfiguration
    - -10 per JWT implementation weakness
    - -20 for service_role key in client code

    **Data Protection (0–100, weight 20%):**
    - Start at 100
    - -25 per committed secret (current or in history)
    - -15 per PII field logged without masking
    - -10 per PII field in API response without need
    - -10 for missing .env in .gitignore

    **Dependencies (0–100, weight 15%):**
    - Start at 100
    - -15 per Critical CVE with reachable code path
    - -8 per High CVE with reachable code path
    - -5 per major version behind on security-sensitive packages
    - -3 per unmaintained dependency

    **Configuration (0–100, weight 10%):**
    - Start at 100
    - -15 for debug mode in production config
    - -10 for stack traces in error responses
    - -10 for missing security headers (CSP, HSTS)
    - -5 for overly verbose error messages

    **Overall** = weighted average. Grade: A (90+) | B (75–89) | C (60–74) | D (40–59) | F (<40)

17. **Generate the report** using the format in AGENT.md.

18. **Write the report:**
    - Save to `qa-reports/security-audit-[date].md`
    - Print summary (score + grade + critical finding count)
    - If previous audit exists, show delta

19. **Provide fix script** for critical/high findings:
    - SQL fixes for RLS gaps
    - Code snippets for auth middleware
    - Dependency upgrade commands
    - Configuration changes
    - Save to `qa-reports/security-fixes-[date].md`

## Key Principles

- **Exploitability over severity** — A Critical CVE in an unused code path is less urgent than a Medium finding in the auth flow. Always assess real-world risk.
- **Fix code, not just findings** — Provide the exact fix for every Critical and High finding. Don't just point out problems.
- **Compound risk matters** — An unprotected route + missing RLS on the same table is worse than either alone. Cross-reference.
- **Git history is attack surface** — Rotated keys don't help if the old key is in git history and the attacker clones the repo.
- **Never modify code during audit** — Report findings and provide fixes. The user reviews and applies.
- **Service role in client code is always Critical** — This single check can reveal complete auth bypass.
- **Read-only SQL only** — Never execute writes against the database during a security audit.
