/**
 * Seed helper for prototype review E2E tests.
 *
 * Uses the Supabase service-role client (bypasses RLS) to insert
 * test data and clean it up after tests complete.
 */
import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'
import path from 'path'

// Load env from project root (.env has SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)
dotenv.config({ path: path.resolve(__dirname, '../../../../.env') })

const supabaseUrl = process.env.SUPABASE_URL
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY

if (!supabaseUrl || !serviceRoleKey) {
  throw new Error('SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in root .env')
}

const supabase: SupabaseClient = createClient(supabaseUrl, serviceRoleKey, {
  auth: { autoRefreshToken: false, persistSession: false },
})

export interface SeedResult {
  prototypeId: string
  featureIds: string[]
  overlayIds: string[]
}

const timestamp = Date.now()

const TEST_FEATURES = [
  {
    name: `E2E Aligned Feature ${timestamp}`,
    overview: 'Test feature expected to be aligned with spec.',
    confirmation_status: 'ai_generated',
  },
  {
    name: `E2E Adjustment Feature ${timestamp}`,
    overview: 'Test feature that needs adjustment.',
    confirmation_status: 'ai_generated',
  },
  {
    name: `E2E OffTrack Feature ${timestamp}`,
    overview: 'Test feature that is off track.',
    confirmation_status: 'ai_generated',
  },
]

function buildOverlayContent(
  featureName: string,
  verdict: 'aligned' | 'needs_adjustment' | 'off_track',
  question: string
) {
  return {
    feature_name: featureName,
    overview: {
      spec_summary: `Spec summary for ${featureName}.`,
      prototype_summary: `Prototype implements ${featureName}.`,
      delta: verdict === 'aligned' ? [] : [`Gap in ${featureName}`],
      implementation_status: verdict === 'aligned' ? 'functional' : 'partial',
    },
    impact: {
      personas_affected: [{ name: 'End User', how_affected: 'Primary user of this feature' }],
      value_path_position: 'Step 1 of 3',
      downstream_risk: verdict === 'off_track' ? 'Blocks downstream features' : 'Low risk',
    },
    gaps:
      verdict === 'aligned'
        ? []
        : [
            {
              question,
              why_it_matters: 'Critical for requirements validation',
              requirement_area: 'business_rules',
            },
          ],
    status: verdict === 'aligned' ? 'understood' : 'partial',
    confidence: verdict === 'aligned' ? 0.95 : verdict === 'needs_adjustment' ? 0.7 : 0.4,
    suggested_verdict: verdict,
  }
}

const OVERLAY_CONFIGS: Array<{
  featureIndex: number
  verdict: 'aligned' | 'needs_adjustment' | 'off_track'
  question: string
}> = [
  { featureIndex: 0, verdict: 'aligned', question: 'Does the login flow match the spec?' },
  {
    featureIndex: 1,
    verdict: 'needs_adjustment',
    question: 'Is the data validation complete?',
  },
  { featureIndex: 2, verdict: 'off_track', question: 'Why is the dashboard missing charts?' },
]

/**
 * Insert test data: 3 features, 1 prototype (analyzed), 3 overlays, 3 questions.
 */
export async function seedPrototypeTestData(projectId: string): Promise<SeedResult> {
  // 1. Insert features
  const featureRows = TEST_FEATURES.map((f) => ({
    project_id: projectId,
    name: f.name,
    overview: f.overview,
    confirmation_status: f.confirmation_status,
  }))

  const { data: features, error: featErr } = await supabase
    .from('features')
    .insert(featureRows)
    .select('id, name')

  if (featErr || !features) throw new Error(`Failed to seed features: ${featErr?.message}`)

  const featureIds = features.map((f: { id: string }) => f.id)

  // 2. Insert prototype
  const { data: proto, error: protoErr } = await supabase
    .from('prototypes')
    .insert({
      project_id: projectId,
      status: 'analyzed',
      deploy_url: 'https://example.com/prototype',
      prompt_text: 'E2E test prototype prompt',
    })
    .select('id')
    .single()

  if (protoErr || !proto) throw new Error(`Failed to seed prototype: ${protoErr?.message}`)

  const prototypeId = proto.id

  // 3. Insert overlays (one per feature)
  const overlayRows = OVERLAY_CONFIGS.map((cfg) => {
    const feature = features[cfg.featureIndex]
    return {
      prototype_id: prototypeId,
      feature_id: feature.id,
      overlay_content: buildOverlayContent(feature.name, cfg.verdict, cfg.question),
      analysis: { summary: `Analysis for ${feature.name}` },
      status: cfg.verdict === 'aligned' ? 'understood' : 'partial',
      confidence: cfg.verdict === 'aligned' ? 0.95 : cfg.verdict === 'needs_adjustment' ? 0.7 : 0.4,
      gaps_count: cfg.verdict === 'aligned' ? 0 : 1,
    }
  })

  const { data: overlays, error: overlayErr } = await supabase
    .from('prototype_feature_overlays')
    .insert(overlayRows)
    .select('id')

  if (overlayErr || !overlays)
    throw new Error(`Failed to seed overlays: ${overlayErr?.message}`)

  const overlayIds = overlays.map((o: { id: string }) => o.id)

  // 4. Insert questions (one per overlay, from OVERLAY_CONFIGS)
  const questionRows = OVERLAY_CONFIGS.filter((cfg) => cfg.verdict !== 'aligned').map(
    (cfg, i) => ({
      // Only non-aligned overlays get questions (aligned has empty gaps)
      overlay_id: overlayIds[cfg.featureIndex],
      question: cfg.question,
      category: 'business_rules',
      priority: 'medium',
    })
  )

  // Also add a question for the aligned overlay to make 3 total
  questionRows.push({
    overlay_id: overlayIds[0],
    question: 'Does the login flow match the spec?',
    category: 'business_rules',
    priority: 'low',
  })

  const { error: qErr } = await supabase.from('prototype_questions').insert(questionRows)

  if (qErr) throw new Error(`Failed to seed questions: ${qErr.message}`)

  return { prototypeId, featureIds, overlayIds }
}

/**
 * Delete seeded data. CASCADE handles children (overlays → questions, sessions → feedback).
 */
export async function teardownPrototypeTestData(
  prototypeId: string,
  featureIds: string[]
): Promise<void> {
  // Delete prototype (cascades to overlays, questions, sessions, feedback)
  const { error: protoErr } = await supabase
    .from('prototypes')
    .delete()
    .eq('id', prototypeId)

  if (protoErr) console.error('Teardown: failed to delete prototype:', protoErr.message)

  // Delete features
  const { error: featErr } = await supabase
    .from('features')
    .delete()
    .in('id', featureIds)

  if (featErr) console.error('Teardown: failed to delete features:', featErr.message)
}

/**
 * Look up a session created for this prototype (used for DB assertions).
 */
export async function getSessionByPrototype(
  prototypeId: string
): Promise<{ id: string; status: string; client_review_token: string | null; session_number: number; client_completed_at: string | null } | null> {
  const { data, error } = await supabase
    .from('prototype_sessions')
    .select('id, status, client_review_token, session_number, client_completed_at')
    .eq('prototype_id', prototypeId)
    .order('session_number', { ascending: false })
    .limit(1)
    .single()

  if (error) return null
  return data
}

/**
 * Get an overlay row directly (for verdict assertion).
 */
export async function getOverlay(
  overlayId: string
): Promise<{ id: string; client_verdict: string | null; consultant_verdict: string | null; client_notes: string | null } | null> {
  const { data, error } = await supabase
    .from('prototype_feature_overlays')
    .select('id, client_verdict, consultant_verdict, client_notes')
    .eq('id', overlayId)
    .single()

  if (error) return null
  return data
}
