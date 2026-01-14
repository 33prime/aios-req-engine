# Frontend Debug Instructions

## Check what data the browser is receiving:

1. Open the Developer Console (Cmd+Option+I on Mac, F12 on Windows)
2. Go to the **Network** tab
3. Refresh the Product Requirements page
4. Look for a request to `/v1/state/prd?project_id=...`
5. Click on it and check the **Response** tab

You should see 4 sections returned.

## To see Features:

Features are on a SEPARATE page, not in Product Requirements tab:
- Navigate to: **Features** tab or `/projects/378cd302-1e6c-4a70-bf87-033121303c74/features`

## To see individual Personas:

The current UI shows personas as **text content** in a PRD section, not as separate persona cards.
The personas section contains:
- Primary user: Sales Representative  
- Secondary user: Sales Manager

## To see Enrichment Details:

Enrichment details only appear AFTER running an enrichment agent:
- In the Product Requirements tab, there should be an "Enrich" button
- Click it to run the enrichment
- After completion, enrichment details will appear in the section detail view

## Quick verification via API:

Run these commands in your terminal to verify the data exists:

```bash
# Check PRD sections
curl "http://localhost:8001/v1/state/prd?project_id=378cd302-1e6c-4a70-bf87-033121303c74" | jq 'length'

# Should return: 4

# Check Features  
curl "http://localhost:8001/v1/state/features?project_id=378cd302-1e6c-4a70-bf87-033121303c74" | jq 'length'

# Should return: 4

# Check VP Steps
curl "http://localhost:8001/v1/state/vp?project_id=378cd302-1e6c-4a70-bf87-033121303c74" | jq 'length'

# Should return: 3
```
