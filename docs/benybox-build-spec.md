# BenyBox — Complete Build Specification

## What This Is

BenyBox is a **family document preparedness platform** for estate planning. Aging parents store critical legal, medical, and insurance documents in a secure vault. Adult children get emergency access. Attorneys get portfolio visibility. The system tells you what you're missing, not just what you have.

**The moat is the rules engine, not AI.** 62% of the intelligence is deterministic rules (state-specific legal requirements, refresh intervals, permission matrices). 12% is AI (document classification, natural language search). 26% is structured data (scoring models, completeness calculations). Don't over-invest in AI when the knowledge base is what no competitor can replicate.

**Reference prototype**: https://pipeline-v2-test.netlify.app — match this design exactly (teal palette, Plus Jakarta Sans headings, DM Sans body, light sidebar navigation).

---

## Desired Outcomes (What Must Be True)

These are the OUTCOMES we're building for — not features. Every screen, component, and function exists to serve one or more of these.

### Margaret (Aging Parent, Primary Owner)
1. **"I know exactly which documents my California situation requires"** — Profile-driven assessment using state x age x status rules. Not a generic checklist — personalized to her divorced, homeowner, two-adult-children, CA-resident profile.
2. **"I can see my preparedness at a glance"** — Vault Completeness Score (weighted: P1 docs = 3x, P2 = 2x). Single number that tells her where she stands.
3. **"My documents stay current without me remembering"** — Staleness detection against document-type-specific refresh intervals. Automated alerts before documents expire.
4. **"My family can access what they need in a crisis"** — Emergency Access Card (printable PDF), family sharing with role-based permissions, audit trail of every access.
5. **"I know how to get documents I'm missing"** — Service provider referrals with cost estimates, prioritized by urgency.

### David (Adult Child Caregiver)
6. **"I can find mom's Healthcare POA in under 90 seconds during an ER visit"** — Emergency access flow, natural language search, mobile-optimized.
7. **"I know mom's document status without calling her"** — Dashboard showing shared vault health, recent changes, approaching deadlines.
8. **"I can prove I have legal authority to act"** — Emergency Access Card with QR verification, document sharing with hospitals/facilities.

### Sarah (Estate Planning Attorney)
9. **"I can see which clients need attention"** — Portfolio dashboard with risk rankings, completeness scores, staleness alerts across all clients.
10. **"I can monitor client vaults without manual check-ins"** — Automated staleness detection, risk-ranked follow-up queue.
11. **"Clients get better outcomes from our relationship"** — BenyBox handles the 80% (basic docs). Sarah handles the 20% (complex estates, trusts, tax planning). BenyBox feeds Sarah the 20%.

### Jake (Unrepresented Individual)
12. **"I understand what I need without paying $500/hour"** — Same assessment engine as Margaret, but with more guidance, simplified language, and DIY paths (LegalZoom, notary, etc.).

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | Next.js 14 (App Router) | SSR for SEO landing pages, client components for app |
| UI | React 18 + Tailwind CSS | Matches prototype exactly |
| Database | Supabase (PostgreSQL + RLS) | Auth, storage, realtime, edge functions built in |
| Auth | Supabase Auth (email + OAuth) | MFA via TOTP for vault security |
| File Storage | Supabase Storage (S3-backed) | Encrypted at rest, signed URLs for access |
| Search | pg_trgm + tsvector (Postgres FTS) | Good enough for document search; no external dependency |
| PDF Generation | @react-pdf/renderer | Emergency Access Cards, export reports |
| Email | Resend | Transactional alerts, share invitations |
| Hosting | Vercel | Edge-optimized, preview deployments |
| Monitoring | Sentry | Error tracking |

**No AI services needed for MVP.** Document classification can be rules-based (filename + user-selected type at upload). Natural language search is a stretch goal — Postgres FTS handles keyword search.

---

## Design System

Match the prototype exactly:

```css
:root {
  --color-primary: #134e4a;    /* Deep teal */
  --color-secondary: #f0fdfa;  /* Teal-tinted white */
  --color-accent: #2dd4bf;     /* Bright teal/cyan */
  --font-heading: 'Plus Jakarta Sans', system-ui, sans-serif;
  --font-body: 'DM Sans', system-ui, sans-serif;
}
```

### Component Library

Build these as reusable components in `components/ui/`:

| Component | Key Props | Notes |
|-----------|-----------|-------|
| Card | header, footer, children, className | `bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md` |
| Badge | variant (default/success/warning/danger/accent) | Warning = amber, Danger = orange (NOT red). `rounded-full` |
| Button | variant (primary/secondary/ghost), size (sm/md/lg) | `inline-flex items-center justify-center gap-2 rounded-lg` |
| Avatar | initials, name, size, src | Circle with initials or image |
| ProgressBar | value (0-100), label | Bar with bg-primary fill |
| Modal | open, onClose, title, children | Overlay with escape handling |
| TabGroup | items [{label, content}] | Underline-style tabs |
| LucideIcon | name, size, className | Wrapper for lucide-react |

### Typography Scale

| Role | Classes | Usage |
|------|---------|-------|
| Page title | `text-2xl font-bold tracking-tight` | One per screen |
| Section header | `text-lg font-semibold` | Card/panel titles |
| Card title | `text-base font-semibold` | Inside cards |
| Body | `text-sm text-gray-700 leading-relaxed` | Paragraphs |
| Label | `text-xs font-medium text-gray-500` | Form labels, metadata |
| Caption | `text-xs text-gray-400` | Timestamps, helpers |

### Status Colors (Always Muted)

| Status | Bg | Text | Use for |
|--------|-----|------|---------|
| Success | bg-emerald-50 | text-emerald-700 | Complete, current, verified |
| Warning | bg-amber-50 | text-amber-700 | Overdue, pending, stale, approaching |
| Danger | bg-orange-50 | text-orange-700 | Failed operations, blocked (NEVER for "overdue") |
| Info | bg-sky-50 | text-sky-700 | Informational |
| Neutral | bg-gray-100 | text-gray-600 | Default, inactive |

---

## Database Schema

### Core Tables

```sql
-- Users (via Supabase Auth, extended with profiles)
create table profiles (
  id uuid primary key references auth.users(id),
  full_name text not null,
  age integer,
  state text,                    -- US state code (CA, FL, etc.)
  marital_status text,           -- single, married, divorced, widowed
  has_children boolean default false,
  owns_home boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Documents
create table documents (
  id uuid primary key default gen_random_uuid(),
  vault_id uuid not null references vaults(id),
  name text not null,
  document_type text not null,     -- 'last_will', 'healthcare_poa', etc.
  category text not null,          -- 'legal', 'medical', 'insurance', 'other'
  priority integer,                -- 1-10 (P1 = most critical)
  status text default 'missing',   -- 'current', 'stale', 'missing', 'pending_review'
  storage_path text,               -- Supabase Storage path
  file_size_bytes bigint,
  mime_type text,
  tags text[] default '{}',
  upload_date timestamptz,
  last_reviewed_at timestamptz,
  refresh_interval_days integer,   -- From document type rules
  state_required boolean default false,
  metadata jsonb default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Vaults (one per user/family)
create table vaults (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references profiles(id),
  name text default 'Family Vault',
  storage_used_bytes bigint default 0,
  storage_limit_bytes bigint default 5368709120, -- 5GB
  encryption_standard text default 'AES-256',
  created_at timestamptz default now()
);

-- Family access permissions
create table family_access (
  id uuid primary key default gen_random_uuid(),
  vault_id uuid not null references vaults(id),
  granted_to_email text not null,
  granted_to_user_id uuid references profiles(id),
  relationship text not null,       -- 'adult_child', 'spouse', 'sibling', 'attorney', 'other'
  access_tier text not null,        -- 'full', 'limited', 'view_only'
  document_categories text[] default '{}', -- For limited access
  granted_at timestamptz default now(),
  expires_at timestamptz,
  status text default 'active',     -- 'active', 'revoked', 'expired'
  emergency_card_generated boolean default false,
  created_at timestamptz default now()
);

-- Third-party shares (doctors, facilities)
create table third_party_shares (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id),
  shared_by uuid not null references profiles(id),
  recipient_email text not null,
  recipient_name text,
  access_level text default 'view_only', -- 'view_only', 'download'
  expires_at timestamptz not null,
  access_token text unique not null,
  accessed_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz default now()
);

-- Audit trail (every access event)
create table audit_events (
  id uuid primary key default gen_random_uuid(),
  vault_id uuid not null references vaults(id),
  actor_id uuid,                    -- null for system events
  actor_name text not null,
  actor_type text not null,         -- 'owner', 'family', 'third_party', 'system'
  event_type text not null,         -- 'view', 'upload', 'download', 'share', 'permission', 'alert'
  document_id uuid references documents(id),
  document_name text,
  description text not null,
  access_method text,               -- 'direct', 'emergency_card', 'share_link'
  ip_address text,
  metadata jsonb default '{}',
  created_at timestamptz default now()
);

-- Checklist items (generated from rules engine per profile)
create table checklist_items (
  id uuid primary key default gen_random_uuid(),
  vault_id uuid not null references vaults(id),
  document_type text not null,
  category text not null,
  priority integer not null,
  display_name text not null,
  description text,
  state_required boolean default false,
  how_to_obtain text,              -- Markdown with provider links
  estimated_cost text,             -- "$89-149" or "Free"
  matched_document_id uuid references documents(id),
  status text default 'missing',   -- 'complete', 'missing', 'stale'
  created_at timestamptz default now()
);

-- Notification preferences
create table notification_prefs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  staleness_alerts boolean default true,
  staleness_frequency text default 'weekly',
  completeness_reminders boolean default true,
  completeness_frequency text default 'monthly',
  family_access_notifications boolean default true,
  third_party_share_alerts boolean default true,
  email_enabled boolean default true,
  sms_enabled boolean default false,
  sms_number text,
  push_enabled boolean default false,
  created_at timestamptz default now()
);
```

### RLS Policies

```sql
-- Vault owners see their own data
create policy "Vault owner access" on documents
  for all using (
    vault_id in (select id from vaults where owner_id = auth.uid())
  );

-- Family members see shared documents based on access tier
create policy "Family member access" on documents
  for select using (
    vault_id in (
      select vault_id from family_access
      where granted_to_user_id = auth.uid()
      and status = 'active'
      and (expires_at is null or expires_at > now())
    )
  );

-- Audit events: vault owners see all, family sees their own
create policy "Audit owner access" on audit_events
  for select using (
    vault_id in (select id from vaults where owner_id = auth.uid())
  );
```

---

## Intelligence Layer (Rules Engine)

### Knowledge System: 50-State Legal Requirements

```typescript
// lib/rules/state-requirements.ts

interface DocumentRequirement {
  type: string           // 'last_will', 'healthcare_poa', etc.
  category: 'legal' | 'medical' | 'insurance' | 'other'
  displayName: string
  priority: number       // 1-10
  stateRequired: boolean
  refreshIntervalDays: number
  description: string
  howToObtain: string    // Markdown
  estimatedCost: string
  conditions?: {         // Only required if conditions match
    minAge?: number
    maritalStatus?: string[]
    hasChildren?: boolean
    ownsHome?: boolean
  }
}

interface StateRuleset {
  state: string
  documents: DocumentRequirement[]
  legalCitations: Record<string, string>  // doc type → citation
  notarizationRules: Record<string, boolean>
}

// Start with top 10 states (covers ~65% of US population):
// CA, TX, FL, NY, PA, IL, OH, GA, NC, MI
// Expand based on user demand
```

### Scoring Model: Vault Completeness

```typescript
// lib/scoring/completeness.ts

function computeVaultScore(checklist: ChecklistItem[]): number {
  const PRIORITY_WEIGHTS = { 1: 3, 2: 3, 3: 2, 4: 2, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1 }

  let totalWeight = 0
  let completedWeight = 0

  for (const item of checklist) {
    const weight = PRIORITY_WEIGHTS[item.priority] ?? 1
    totalWeight += weight
    if (item.status === 'complete') {
      completedWeight += weight
    }
  }

  return totalWeight > 0 ? Math.round((completedWeight / totalWeight) * 100) : 0
}
```

### Decision Logic: Profile → Checklist Router

```typescript
// lib/rules/checklist-router.ts

function generateChecklist(profile: Profile): ChecklistItem[] {
  const stateRules = getStateRuleset(profile.state)
  const items: ChecklistItem[] = []

  for (const doc of stateRules.documents) {
    // Check conditions
    if (doc.conditions?.minAge && profile.age < doc.conditions.minAge) continue
    if (doc.conditions?.maritalStatus && !doc.conditions.maritalStatus.includes(profile.maritalStatus)) continue
    if (doc.conditions?.hasChildren === true && !profile.hasChildren) continue
    if (doc.conditions?.ownsHome === true && !profile.ownsHome) continue

    items.push({
      documentType: doc.type,
      category: doc.category,
      priority: doc.priority,
      displayName: doc.displayName,
      description: doc.description,
      stateRequired: doc.stateRequired,
      howToObtain: doc.howToObtain,
      estimatedCost: doc.estimatedCost,
      refreshIntervalDays: doc.refreshIntervalDays,
      status: 'missing'
    })
  }

  return items.sort((a, b) => a.priority - b.priority)
}
```

### Decision Logic: Staleness Detection

```typescript
// lib/rules/staleness.ts

function checkStaleness(doc: Document): 'current' | 'approaching' | 'stale' {
  if (!doc.uploadDate || !doc.refreshIntervalDays) return 'current'

  const daysSinceUpload = daysBetween(doc.uploadDate, new Date())
  const threshold = doc.refreshIntervalDays

  if (daysSinceUpload > threshold) return 'stale'
  if (daysSinceUpload > threshold * 0.8) return 'approaching'
  return 'current'
}
```

### Decision Logic: Permission Validation

```typescript
// lib/rules/permissions.ts

type AccessTier = 'full' | 'limited' | 'view_only'

interface AccessDecision {
  canView: boolean
  canDownload: boolean
  categories: string[]  // Which categories they can access
}

function validateAccess(
  permission: FamilyAccess,
  document: Document
): AccessDecision {
  if (permission.status !== 'active') return { canView: false, canDownload: false, categories: [] }
  if (permission.expiresAt && new Date() > permission.expiresAt) return { canView: false, canDownload: false, categories: [] }

  switch (permission.accessTier) {
    case 'full':
      return { canView: true, canDownload: true, categories: ['legal', 'medical', 'insurance', 'other'] }
    case 'limited':
      const canAccess = permission.documentCategories.includes(document.category)
      return { canView: canAccess, canDownload: canAccess, categories: permission.documentCategories }
    case 'view_only':
      return { canView: true, canDownload: false, categories: ['legal', 'medical', 'insurance', 'other'] }
  }
}
```

---

## Pages & Routes

### App Shell
- **Layout**: Light sidebar (w-64, white bg, border-r border-gray-200)
- **Logo**: "BenyBox" in font-heading font-bold text-lg, deep teal
- **User menu**: Avatar + name + role at bottom of sidebar
- **Content area**: bg-gray-50, p-8

### Route Map

| Route | Page | Nav Section | Icon | Purpose |
|-------|------|-------------|------|---------|
| `/onboarding` | OnboardingPage | GET STARTED | ClipboardList | Profile wizard → assessment |
| `/` | DashboardPage | MY VAULT | LayoutDashboard | Vault health overview |
| `/documents` | DocumentsPage | MY VAULT | FolderOpen | Document browser + upload |
| `/gaps` | GapsPage | MY VAULT | AlertTriangle | Missing docs + referrals |
| `/family` | FamilyPage | FAMILY | Users | Family members + sharing |
| `/audit` | AuditPage | FAMILY | ShieldCheck | Access audit trail |
| `/settings` | SettingsPage | ACCOUNT | Settings | Profile, notifications, security |
| `/attorney` | AttorneyPage | (attorney role only) | Briefcase | Client portfolio dashboard |

### Page Specifications

#### 1. Onboarding (`/onboarding`) — 3-Step Wizard

**Step 1: Your Profile**
- Full name, age, state (dropdown with 50 states), marital status, has children toggle, owns home toggle
- State selection shows contextual callout (e.g., "California is a community property state — this affects which documents you need")
- Inline validation with green checkmarks

**Step 2: Your Assessment**
- Runs checklist router with profile → generates personalized document list
- Shows vault completeness score (0% for new user) as circular progress ring
- Grid of checklist items as cards: priority badge, name, category badge, "CA Required" if applicable, "Missing" status
- This is the WOW moment — "I didn't know I needed a Transfer-on-Death deed"

**Step 3: Vault Ready**
- Summary stats: Documents Needed, State-Specific count, Uploaded (0), Estimated Cost range
- "Go to Your Vault" CTA button

#### 2. Dashboard (`/`) — Vault Health Overview

**Metric Grid (4 cards)**:
- Vault Completeness Score — large circular SVG progress ring with percentage, doc count
- Missing Documents — count with priority breakdown, border-left-4 amber
- Stale Documents — count with names, border-left-4 amber
- Family Members with Access — count with names

**Document Coverage by Category** — horizontal progress bars (Legal, Medical, Insurance, Other) with fraction labels

**Activity Feed** — 6-8 recent events with colored icons, actor name, action, document badge, timestamp. System events (staleness alerts, score updates) show agent attribution subtly.

**Priority Gaps** — top 3 missing documents as expandable cards with "Why you need this" and provider links

#### 3. Documents (`/documents`) — Document Management

**Category Tabs**: Legal (count), Medical (count), Insurance (count), Other (count)

**Search + Filters**: Text search, status filter chips (All/Current/Stale/Missing), priority filter

**Document Table**: Columns — Name, Type, Priority, Status (badge), Tags (teal pills), Upload Date, Actions (view/share/refresh icons or "Upload Now" for missing)

**Upload Flow** (modal, 3 steps):
1. Select document type from checklist dropdown (or custom type)
2. Drag-and-drop file upload (PDF, JPG, PNG — max 50MB)
3. Confirm type + category auto-detection, add/remove tags, save

**Share Flow** (modal): Select document → recipient email → access level → expiration → send

#### 4. Gaps & Help (`/gaps`) — Missing Documents + Referrals

**Gap Summary Stats**: Missing count, Stale count, Completeness %, estimated cost to close all gaps

**Gap Cards (2-column grid)**: Each card shows:
- Priority badge + category badge
- Document name + description of why it's needed
- "How to Obtain" section with 2-3 provider options (name, cost, estimated time)
- Projected score impact badge ("+3% if uploaded")
- "I Have This — Upload Now" button

#### 5. Family Access (`/family`) — Sharing & Permissions

**Left panel (1/3)**: Family member list with avatars, names, relationships, access tier badges, last active time. "Invite Family Member" button.

**Right panel (2/3)**: Selected member detail — access tier, document categories, permission date, last activity, Emergency Access Card status. Actions: downgrade, revoke (with confirmation modal + audit notice).

**Invite Wizard (4 steps)**:
1. Name + email + relationship
2. Access level (Full/Limited/View-Only) + optional category selection
3. Review & consent checkbox
4. Emergency Access Card preview (branded card with QR placeholder, document counts, authorized contact info)

**Third-Party Shares section**: Active shares with recipient, document, access level, expiration, revoke/extend buttons

#### 6. Audit Log (`/audit`) — Access History

**Summary Stats**: Total events, unique accessors, active third-party shares, suspicious events flagged

**Timeline View**: Vertical timeline with colored dots per actor, filterable by date range, accessor, event type

**Table View**: Timestamp, Accessor, Role, Document, Event Type (colored badge), Access Method, IP Address. Searchable, filterable, paginated.

**Export**: PDF, CSV, JSON download

#### 7. Settings (`/settings`) — Account Management

**Profile Section**: Same fields as onboarding. State change triggers re-assessment warning.

**Notification Preferences**: 4 toggles (staleness alerts, completeness reminders, family access, third-party share) with frequency dropdowns and delivery method options (email, SMS, push)

**Security**: 2FA toggle (email OTP or authenticator app), change password, last login info

**Data & Storage**: Storage usage bar, encryption info, plan info, data export link

**Pricing**: 3-tier display (Personal $9/mo, Family $12/mo, Estate Pro $29/mo)

#### 8. Attorney Portal (`/attorney`) — B2B Dashboard (Future / H2)

**Client Table**: Columns — Client Name, State, Vault Score (progress bar), Missing Docs, Stale Docs, Risk Level (badge), Last Updated, Actions

**Filters**: Search, risk level, state

**Client Detail**: Click to expand — vault completeness breakdown, gap list, staleness alerts, recent activity. "Send Reminder" and "Schedule Review" actions.

---

## Security Requirements

These are the "security issues" that need solving:

1. **Encryption at rest**: All files in Supabase Storage encrypted (AES-256). Database fields with PII encrypted at application level.
2. **Encryption in transit**: TLS 1.3 everywhere. No HTTP.
3. **Row-Level Security**: Every table has RLS policies. Users see only their own data + data shared with them.
4. **MFA required for vault access**: TOTP-based 2FA for all document operations.
5. **Signed URLs for file access**: No permanent file URLs. Short-lived signed URLs (15 min) generated per request.
6. **Share link security**: Third-party shares use unique tokens with expiration. One-time-use option available.
7. **Emergency Access**: Emergency Access Cards use a verification flow (QR → authenticate → access). Not a bypass of security — a pre-authorized access path.
8. **Audit everything**: Every document view, download, share, and permission change logged with actor, timestamp, IP, method.
9. **CCPA/HIPAA awareness**: Medical documents flagged as PHI. California residents get data export/deletion rights.
10. **Session management**: Short session tokens (1hr), refresh tokens (7d), automatic logout on inactivity (15min for vault pages).

---

## API Routes (Next.js Route Handlers)

```
POST /api/auth/signup          — Create account + profile
POST /api/auth/signin          — Login
POST /api/auth/mfa/setup       — Enable 2FA
POST /api/auth/mfa/verify      — Verify 2FA code

GET  /api/profile              — Get current user profile
PUT  /api/profile              — Update profile (triggers re-assessment)

GET  /api/vault                — Get vault summary (score, counts)
GET  /api/vault/checklist      — Get personalized checklist
POST /api/vault/reassess       — Re-run assessment (after profile change)

GET  /api/documents            — List documents (with filters)
POST /api/documents/upload     — Upload document (multipart)
PUT  /api/documents/:id        — Update document metadata
DELETE /api/documents/:id      — Delete document

GET  /api/documents/:id/download — Get signed download URL
POST /api/documents/:id/share   — Create third-party share
DELETE /api/shares/:id          — Revoke share

GET  /api/family               — List family access records
POST /api/family/invite        — Send invitation
PUT  /api/family/:id           — Update access tier
DELETE /api/family/:id         — Revoke access

POST /api/family/:id/emergency-card — Generate Emergency Access Card PDF
GET  /api/family/emergency-card/:token — Verify + access via emergency card

GET  /api/audit                — List audit events (with filters)
GET  /api/audit/export/:format — Export audit log (pdf/csv/json)

GET  /api/gaps                 — Get gap analysis
GET  /api/gaps/:type/providers — Get service providers for a document type

GET  /api/settings/notifications — Get notification prefs
PUT  /api/settings/notifications — Update notification prefs
```

---

## Implementation Order

### Phase 1: Core Vault (Week 1-2)
1. Supabase project setup, auth, RLS policies
2. Profile onboarding wizard (3 steps)
3. Rules engine: CA state requirements (start with 1 state)
4. Checklist router: profile → personalized document list
5. Document upload + storage + categorization
6. Vault completeness score calculation
7. Dashboard with metrics + activity feed

### Phase 2: Sharing & Security (Week 2-3)
8. Family access: invite, accept, permission management
9. Emergency Access Card generation (PDF)
10. Third-party document sharing with expiring links
11. Audit trail: log every access event
12. MFA setup and enforcement
13. Signed URLs for all file access

### Phase 3: Intelligence (Week 3-4)
14. Staleness detection: cron job checking refresh intervals
15. Gap analysis page with provider referrals
16. Notification system: email alerts for staleness, access, etc.
17. Multi-state expansion: add TX, FL, NY, PA (top 5 states)

### Phase 4: Attorney Portal (Week 4-5)
18. Attorney role + portal dashboard
19. Client portfolio view with risk rankings
20. Attorney-specific sharing flows

---

## KPI Targets (Business Drivers)

| Metric | Target | Priority |
|--------|--------|----------|
| Profile onboarding + assessment completion rate | 75%+ of registered users | High |
| Average documents uploaded per user (30 days) | 5+ documents | High |
| Family member invite rate | 50%+ share with at least 1 member | P1 |
| Assessment-to-upload conversion | 60%+ upload at least 1 doc | High |

## Critical Constraints

| Constraint | Type | Severity | Implication |
|-----------|------|----------|-------------|
| CCPA/HIPAA Data Residency | Regulatory | **CRITICAL** | US-only hosting, encryption at rest, medical docs = PHI, right to deletion |
| Third-Party Sharing Audit Trail | Technical | High | Every share event logged with consent record, 7-year retention |
| Emergency Access Card Liability | Regulatory | High | Legal disclaimer on EAC generation, not legal advice, consent checkbox |
| AI Tagging Accuracy & Liability | Strategic | High | Auto-tags are suggestions, user confirms before persistence. No legal advice. |
| Secure Storage Cost Ceiling | Budget | Medium | Supabase Storage (S3-backed) keeps costs low vs. custom infra |

## Competitive Landscape

**No direct competitors.** First-to-market in the family-focused assessment + storage + sharing space.

Existing tools address pieces but not the whole:
- **Dropbox/Google Drive**: Storage, no assessment, no legal guidance
- **Everplans**: Estate planning but $$$, no real-time scoring
- **Trust & Will**: Document creation, no vault/sharing
- **LegalZoom**: Document drafting, no ongoing management
- **Clio/MyCase**: Attorney-side only, no family access

BenyBox's moat: the **rules engine** (50-state legal requirements → personalized checklist) combined with **family sharing** (role-based access + Emergency Access Card). No competitor combines assessment + organization + multi-party sharing.

---

## Key Decisions Already Made

- **Rules over AI**: The assessment engine is a deterministic rules engine, not an LLM. State x age x status = document list. No AI needed.
- **Start with 1 state (California)**: Validate with real users before expanding. Margaret is a CA resident.
- **No AI document classification for MVP**: User selects document type from checklist dropdown at upload. Auto-classification is a future enhancement.
- **Badge danger = orange, not red**: "Overdue" and "stale" are warnings (amber/orange), not errors.
- **Emergency Access Card is a pre-authorized path**: Not a security bypass. Family members are pre-granted access; the card just makes it fast during a crisis.
- **Audit everything from day 1**: Every access event logged. This is table stakes for a document vault handling legal/medical records.
- **Pricing tiers**: Personal ($9/mo, 5GB), Family ($12/mo, 25GB), Estate Pro ($29/mo, 100GB). Start with Family as default.

---

## What NOT to Build

- No AI chatbot / conversational interface
- No document summarization (H2 feature)
- No hospital integration / HL7/FHIR (H3)
- No insurance company data pipes (H3)
- No attorney creation workflow / document drafting (H3)
- No mobile app (responsive web is sufficient for MVP)
- No complex permissions UI beyond 3 tiers (full/limited/view-only)
- No social features, sharing feeds, or community
- No blockchain, NFTs, or crypto anything
