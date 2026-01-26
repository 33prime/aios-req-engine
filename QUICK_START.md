# 🚀 Quick Start - Business Driver Enrichment

## How to Test the New Commands

### Step 1: Open the Workbench
Navigate to: `http://localhost:3000`

### Step 2: Select a Project
Click on any project that has business drivers (KPIs, Pain Points, or Goals)

### Step 3: Open AI Assistant
Click the chat/assistant icon in the project view

### Step 4: Test Commands

#### Option A: Enrich All at Once
```
/enrich-business-drivers
```
This enriches ALL business drivers (KPIs + pains + goals) in one command.

#### Option B: Enrich by Type
```
/enrich-kpis          ← Just KPIs
/enrich-pain-points   ← Just pain points
/enrich-goals         ← Just goals
```

---

## What You'll See

### Before Running Command:
```
Strategic Foundation Tab
├─ KPIs (5)
│  ├─ Revenue Growth Rate [AI Draft] [Low confidence]
│  ├─ Customer Acquisition Cost [AI Draft] [Low confidence]
│  └─ Monthly Recurring Revenue [AI Draft] [Low confidence]
```

### After Running `/enrich-kpis`:
```
AI Assistant Response:
┌──────────────────────────────────────────────┐
│ **KPI Enrichment Complete**                 │
│                                              │
│ ✓ Enriched 5 KPIs                           │
│                                              │
│ KPIs now include:                            │
│ - Baseline and target values                │
│ - Measurement methods                        │
│ - Data sources                               │
│ - Responsible teams                          │
│                                              │
│ Refresh the Strategic Foundation tab to see │
│ updates.                                     │
└──────────────────────────────────────────────┘
```

### Enriched Card View (Expanded):
```
┌─────────────────────────────────────────────────────┐
│ 🎯 Revenue Growth Rate ✨                           │
│ [Confirmed] [High] [Enrich All (0)]                 │
│                                                     │
│ 📊 Measurement Details                              │
│ ├─ Baseline: 15% YoY                                │
│ ├─ Target: 40% YoY                                  │
│ ├─ Method: (Current MRR - Previous MRR) / Previous │
│ ├─ Frequency: Monthly                               │
│ ├─ Data Source: Stripe MRR reports                 │
│ └─ Team: Growth Team                                │
│                                                     │
│ 💼 Business Impact                                  │
│ ├─ Associated Features (2):                         │
│ │  • Referral Program                               │
│ │  • Pricing Tiers                                  │
│ └─ Related Pains (1):                                │
│    • Customer churn rate too high                   │
│                                                     │
│ 📝 Evidence (3)                                     │
│ "We need to accelerate growth to 40% YoY..."       │
│ [View source]                                       │
└─────────────────────────────────────────────────────┘
```

---

## Color Scheme

All elements now use **green shades only**:

| Element | Color Preview |
|---------|---------------|
| KPI cards | 🟢 Bright emerald green |
| Pain cards | 🟢 Forest/dark green |
| Goal cards | 🟢 Teal green |
| Severity badges | 🟢 Green gradient (dark → light) |
| Enrich buttons | 🟢 Type-specific green |
| Sparkle icon ✨ | 🟢 Emerald |

**No blue, red, yellow, or amber colors!**

---

## Available Commands

### Basic Commands:
- `/help` - Show all commands
- `/project-status` - View project overview

### Enrichment Commands:
- `/enrich-kpis` - Enrich KPIs with measurements
- `/enrich-pain-points` - Enrich pains with severity/impact
- `/enrich-goals` - Enrich goals with timeframes/criteria
- `/enrich-business-drivers` - Enrich ALL drivers at once

### Other AI Commands:
- `/run-foundation` - Extract business drivers from signals
- `/enrich-features` - Enrich all features
- `/enrich-personas` - Enrich all personas

---

## Expected Behavior

### Enrichment Process:
1. **Duration:** 10-30 seconds (depending on count)
2. **Model:** Claude Sonnet 4
3. **Concurrency:** Up to 5 drivers enriched in parallel
4. **Auto-refresh:** Page suggests refresh after completion

### What Gets Enriched:

**KPIs get:**
- Baseline value (current state)
- Target value (desired state)
- Measurement method (how to calculate)
- Tracking frequency (daily/weekly/monthly)
- Data source (where data comes from)
- Responsible team (who owns it)

**Pain Points get:**
- Severity (critical/high/medium/low)
- Frequency (constant/daily/weekly/monthly/rare)
- Affected users (who experiences it)
- Business impact (quantified cost)
- Current workaround (how users cope)

**Goals get:**
- Timeframe (when to achieve)
- Success criteria (what defines success)
- Dependencies (prerequisites)
- Owner (who's responsible)

### Merge Detection:
- AI reviews existing drivers
- Suggests merges if duplicates found
- Includes reasoning in response
- You decide whether to merge

---

## Troubleshooting

### Command not found?
- Make sure you're in the AI Assistant chat
- Commands start with `/` (slash)
- Type `/help` to see available commands

### No enrichment happening?
- Check that drivers exist (go to Strategic Foundation tab)
- Verify they're not already enriched (look for ✨ sparkle icon)
- Backend must be running (port 8000)

### Colors still showing blue/red/yellow?
- Hard refresh the browser: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
- Clear cache if needed

---

## Quick Test Script

Run these commands in order to fully test:

```bash
# 1. Check commands are loaded
/help

# 2. See project status
/project-status

# 3. Enrich all business drivers
/enrich-business-drivers

# 4. Wait ~20 seconds for completion

# 5. Refresh Strategic Foundation tab

# 6. Click on any enriched driver (has ✨)

# 7. Verify:
#    - Green colors throughout
#    - Detailed enrichment data
#    - Multiple fields populated
#    - Evidence links working
```

---

## Success Criteria

✅ Commands execute without errors
✅ Enrichment completes in <30 seconds
✅ Enriched data shows in expanded cards
✅ All colors are green shades
✅ 6+ fields populated per driver type
✅ Evidence attribution visible
✅ Related features auto-linked

---

**Ready to test!** 🎉

Open `http://localhost:3000`, select a project, and run `/enrich-business-drivers` in the AI Assistant.
