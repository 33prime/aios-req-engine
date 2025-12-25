# Personas Enhancement

## Overview

The personas feature provides two viewing modes for personas in the PRD:
1. **Text View**: Traditional enriched text format
2. **Card Grid View**: Visual card layout with expandable modals

## Viewing Modes

### Text View

Displays personas as enriched text content, maintaining the traditional PRD format. Useful for:
- Quick reading and scanning
- Copy/paste into documents
- Linear narrative flow

### Card Grid View

Displays personas as interactive cards in a 2-column grid. Each card shows:
- Avatar placeholder
- Name and role
- Brief description
- Key goals preview

**Click any card** to open a detailed modal with:
- Full demographics
- Psychographics
- Goals and pain points
- Related features
- Related VP steps
- Evidence sources

## UI Components

### PersonaCard

Compact card component for grid display:

```tsx
<PersonaCard
  persona={persona}
  onClick={() => setSelectedPersona(persona)}
/>
```

### PersonaModal

Full-screen modal with complete persona details:

```tsx
<PersonaModal
  persona={selectedPersona}
  relatedFeatures={getRelatedFeatures(selectedPersona)}
  relatedVpSteps={getRelatedVpSteps(selectedPersona)}
  isOpen={!!selectedPersona}
  onClose={() => setSelectedPersona(null)}
/>
```

## Persona Data Structure

Personas are stored in the `prd_sections` table where `slug='personas'`.

### Structured Format (Preferred)

```json
{
  "enrichment": {
    "enhanced_fields": {
      "personas": [
        {
          "name": "Sarah Chen",
          "role": "Product Manager",
          "demographics": {
            "age_range": "30-40",
            "location": "San Francisco Bay Area",
            "company_size": "Series B startup"
          },
          "psychographics": {
            "goals": ["Launch products faster", "Reduce technical debt"],
            "pain_points": ["Misaligned stakeholders", "Scope creep"],
            "values": ["Data-driven decisions", "User feedback"]
          },
          "related_features": ["feature-uuid-1", "feature-uuid-2"],
          "related_vp_steps": ["vp-step-uuid-1"]
        }
      ]
    }
  }
}
```

### Text Format (Fallback)

If personas are stored as markdown text, the `parsePersonasFromText()` utility extracts:
- Names (headers starting with ##)
- Roles (first line after name)
- Demographics (bullets under "Demographics" section)
- Goals and pain points (extracted from text)

## Parsing Logic

The `parsePersonas()` function in `lib/persona-utils.ts`:

1. **Try structured data first**: Check `enrichment.enhanced_fields.personas`
2. **Fallback to text parsing**: Parse from `enrichment.enhanced_fields.content` or `fields.content`
3. **Normalize format**: Convert all formats to consistent Persona objects

## Related Entity Linking

The modal shows related features and VP steps mentioned in the persona:

### Related Features

Features are linked by:
- UUID references in `persona.related_features`
- Name matches in persona description

### Related VP Steps

VP steps are linked by:
- UUID references in `persona.related_vp_steps`
- Journey mapping in persona psychographics

## Toggle Implementation

In the PRD detail view, personas section has a toggle button:

```tsx
const [personasViewMode, setPersonasViewMode] = useState<'text' | 'cards'>('text')

// Toggle buttons in header
<ToggleGroup>
  <Button onClick={() => setPersonasViewMode('text')}>Text View</Button>
  <Button onClick={() => setPersonasViewMode('cards')}>Card View</Button>
</ToggleGroup>

// Conditional rendering
{personasViewMode === 'text' ? (
  <EnrichedTextView content={section.enrichment.enhanced_fields.personas} />
) : (
  <PersonasCardGrid personas={personas} />
)}
```

## Best Practices

### For AI Enrichment

When enriching personas, use the structured format:
- Provide clear demographics (age, location, role)
- List specific goals and pain points
- Reference related features and VP steps by UUID
- Include evidence sources

### For Consultants

- Use **Text View** for initial reading and understanding
- Switch to **Card View** for presentations and client reviews
- Click cards to explore deep context and relationships
- Export personas from modal for external documents

## Future Enhancements

- Persona journey mapping visualization
- Import personas from external sources (interviews, surveys)
- Compare personas across projects
- AI-suggested persona refinements based on new signals
