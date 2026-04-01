# Prototype Design Quality Reference

This reference is loaded into every builder prompt. Follow it exactly.

## ANTI-SLOP RULES (Highest Priority)

These patterns make prototypes look "obviously AI-generated". NEVER do them.

### Banned Color Patterns
- No `bg-indigo-500`, `bg-indigo-600`, `bg-violet-500` for primary actions
- No purple-to-blue gradients anywhere
- No neon cyan (#22d3ee), hot pink (#f472b6), electric purple (#a855f7)
- No gradient backgrounds on buttons
- No colored shadows (e.g. `shadow-indigo-500/25`)
- No screaming red badges for non-error states — "Overdue" is amber, not red
- Status colors must be MUTED: use `-50` bg with `-700` text (e.g. `bg-amber-50 text-amber-700`), never saturated fills

### Banned Layout Patterns
- No hero sections inside dashboards or app UIs
- No decorative copy ("Streamline your workflow", "Operational clarity")
- No "three boxes with icons" landing page cliches
- No decorative blobs, glows, or glassmorphism panels
- No donut charts without real data driving them
- No `rounded-full` on cards or containers (pill-shaped cards = AI tell)
- No `shadow-2xl` or `shadow-lg` on cards (max: `shadow-sm` or `shadow-md` on hover)

### Banned Typography
- No UPPERCASE EYEBROW LABELS on everything — use them sparingly (1-2 per screen max)
- No safe weight contrast (400 vs 600) — use 400 body vs 700-800 headings
- No multiple decorative fonts — one heading font, one body font, period

### Banned Interactions
- No bouncy/spring animations
- No `translateX`/`translateY` hover transforms on buttons
- No spinning loaders — use skeleton shimmer
- No animated underlines on nav items

---

## HARD RULES (Never violate)

### Typography Scale

| Role            | Tailwind Classes                              | Usage                        |
|-----------------|-----------------------------------------------|------------------------------|
| Page title      | text-2xl font-bold tracking-tight             | One per screen, top-left     |
| Section header  | text-lg font-semibold                         | Cards, panel titles          |
| Card title      | text-base font-semibold                       | Inside cards                 |
| Body            | text-sm text-gray-700 leading-relaxed         | Paragraphs, descriptions     |
| Label           | text-xs font-medium text-gray-500             | Form labels, metadata        |
| Caption/helper  | text-xs text-gray-400                         | Below inputs, timestamps     |

Never use text-3xl or larger in content areas.
Never use font-bold on body text.
Always use tracking-tight on page titles.
Use uppercase tracking-wide labels ONLY for table headers and form section dividers.

### Spacing System (8px grid)

- Between major sections: space-y-8
- Between cards in a grid: gap-6
- Inside cards: p-6
- Between elements inside a card: space-y-4
- Form field groups: space-y-5
- Between a label and its input: space-y-1.5
- Page padding: p-8

Never use p-2 or p-3 on cards (too cramped).
Never use gap-2 between cards (too tight).
Every spacing value must come from the Tailwind scale (multiples of 4px).

### Content Background

Content area MUST be light: bg-white, bg-gray-50, or bg-slate-50.
Dark backgrounds are ONLY for sidebar navigation.
Forms on dark backgrounds are invisible — never do this.

### Border Radius Rules

- Cards: rounded-xl (12px) maximum. Never rounded-2xl or rounded-3xl.
- Buttons: rounded-lg (8px). Match the card feel.
- Inputs: rounded-lg (8px).
- Badges: rounded-full is OK (they're small).
- Avatars: rounded-full is OK.
- Everything else: rounded-lg default.

### Shadow Rules

- Cards at rest: shadow-sm (subtle)
- Cards on hover: shadow-md (medium)
- Modals/dropdowns: shadow-lg (only these)
- NEVER use shadow-xl or shadow-2xl on cards
- NEVER use colored shadows
- Prefer 1px borders (border-gray-100) over shadows for separation

---

## BUTTON + ICON ALIGNMENT (Critical)

Misaligned icons in buttons are the single most visible quality issue.

**Every button with an icon MUST use this exact pattern:**
```tsx
<Button variant="primary" size="md" onClick={handler}>
  <LucideIcon name="Plus" size={16} className="shrink-0" />
  Label Text
</Button>
```

If building a custom button (not using the Button component):
```tsx
<button className="inline-flex items-center gap-2 px-4 py-2.5 ...">
  <LucideIcon name="Plus" size={16} className="shrink-0" />
  <span>Label Text</span>
</button>
```

**Rules:**
- ALWAYS `inline-flex items-center gap-2` — icons must sit BESIDE text, never above
- ALWAYS `shrink-0` on icons inside flex containers
- Icon sizes: 14px in `sm` buttons, 16px in `md` buttons, 18px in `lg` buttons
- NEVER use `flex-col` inside a button
- NEVER stack icon above text — this is the #1 visual defect
- Arrow icons (→) go AFTER text: `<span>Label</span> <LucideIcon name="ArrowRight" />`

**Action button rows (multiple buttons side by side):**
```tsx
<div className="flex items-center gap-3">
  <Button variant="primary" size="sm">
    <LucideIcon name="Upload" size={14} className="shrink-0" />
    Upload
  </Button>
  <Button variant="secondary" size="sm">
    <LucideIcon name="Share2" size={14} className="shrink-0" />
    Share
  </Button>
</div>
```

---

## COLOR DISCIPLINE

### How to Use the Brand Color
- Primary color: primary buttons, active nav, chart accent, icon badge backgrounds (primary/10)
- Use `bg-primary` for ONE main CTA per screen, not every button
- Secondary buttons: `bg-white border border-gray-200 text-gray-700 hover:bg-gray-50`
- Ghost buttons: `text-gray-600 hover:bg-gray-100`

### Status Colors (Always Muted)
Use light backgrounds with dark text. NEVER use saturated fills.

**CRITICAL: "Overdue", "Pending", "Due soon", "Approaching deadline" are WARNING states (amber), NOT errors (red).**
**Red is ONLY for: system errors, failed operations, blocked/critical security issues.**
**When in doubt, use amber (warning) not red (danger).**

| Status    | Background      | Text             | When to use                    |
|-----------|----------------|------------------|--------------------------------|
| Success   | bg-emerald-50  | text-emerald-700 | Complete, active, verified     |
| Warning   | bg-amber-50    | text-amber-700   | Pending, overdue, needs review |
| Error     | bg-red-50      | text-red-700     | Failed, blocked, critical only |
| Info      | bg-sky-50      | text-sky-700     | Informational, neutral status  |
| Neutral   | bg-gray-100    | text-gray-600    | Default, inactive, archived    |

**"Overdue" is a WARNING (amber), not an error (red).**
Red is reserved for system errors and truly critical blocked states.

### Accent Color Usage
- Icon background circles: `bg-primary/10` with `text-primary`
- Selected/active rows: `bg-primary/5`
- Left border highlights: `border-l-2 border-primary`
- Chart accents and data visualization
- NEVER scatter bright colors decoratively — every color must convey meaning

---

## COMPONENT STANDARDS

### Cards
```
bg-white rounded-xl shadow-sm border border-gray-100
hover:shadow-md transition-shadow duration-200
```
Padding: p-6 always. Never p-2 or p-3.

### Form Inputs
```
bg-white border border-gray-200 rounded-lg px-4 py-2.5 text-sm
placeholder:text-gray-400
focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none
```
Labels above inputs with `space-y-1.5` gap.

### Tables
- Header: `bg-gray-50/80 text-xs font-medium text-gray-500 uppercase tracking-wide`
- Rows: `hover:bg-gray-50 transition-colors`
- Dividers: `divide-y divide-gray-100`
- Cell padding: `px-6 py-4`

### Data Cells in Tables
- Numbers right-aligned, text left-aligned
- Status columns use Badge component (never plain text)
- Action columns: icon buttons only, no text labels in table rows

---

## FORM & ONBOARDING PATTERNS

### Multi-Step Wizard (for onboarding, setup, guided flows)
```tsx
// Step indicator at top
<div className="flex items-center gap-2 mb-8">
  {steps.map((step, i) => (
    <div key={i} className="flex items-center gap-2">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-medium ${
        i < currentStep ? 'bg-primary text-white'
        : i === currentStep ? 'bg-primary/10 text-primary border-2 border-primary'
        : 'bg-gray-100 text-gray-400'
      }`}>
        {i < currentStep ? <LucideIcon name="Check" size={16} /> : i + 1}
      </div>
      {i < steps.length - 1 && (
        <div className={`w-12 h-0.5 ${i < currentStep ? 'bg-primary' : 'bg-gray-200'}`} />
      )}
    </div>
  ))}
</div>

// One section per step, 1-3 fields max
// Always show: Back button (secondary) + Continue button (primary)
// Final step: "Complete" or "Get Started" with celebration state
```

**Rules:**
- 3-5 steps maximum for onboarding
- 1-3 fields per step (never a wall of fields)
- Progress visible at all times (step dots or numbered steps)
- Each step has exactly ONE primary action
- Back button always available (except step 1)
- Final step shows a completion/celebration state
- Use progressive disclosure — show advanced options only when toggled
- Real-time validation per field, not at the end

### Form Sections
- Group related fields with a section header (`text-base font-semibold mb-4`)
- Max 6 fields visible at once — use tabs or accordion for more
- Select/dropdown for 3-7 options, radio group for 2-4 options
- Toggle switches for boolean settings, not checkboxes

---

## APPROVED ANIMATIONS (pick 0-3 per screen)

1. Fade-in on mount: `opacity-0 -> opacity-100, duration-300, ease-out`
2. Hover lift on cards: `hover:shadow-md transition-shadow duration-200`
3. Progress bar fill: `transition-all duration-1000 ease-out` on width
4. Skeleton shimmer: `animate-pulse` on `bg-gray-200 rounded` blocks

**Transition timing:**
- Hover/focus: 150ms
- Layout changes: 200ms
- Page transitions: 300ms
- Easing: always ease-out for entrances

Do NOT use: bouncing, sliding from off-screen, spring physics, spinning, or complex keyframes.

---

## CREATIVE FREEDOM

You have discretion over:
- Layout pattern choice (split, grid, sidebar-detail, wizard, timeline)
- Where accent color highlights appear (left borders, icon circles, badge fills)
- Chart types and data visualization approach
- Icon selection from Lucide React
- Component arrangement within sections
- Whether to use subtle card borders or shadows for hierarchy
- Mock data specifics (names, values) as long as they're domain-realistic
