-- migrations/0082_client_packages.sql
-- Description: Create client packages system for AI-synthesized questions
-- Date: 2026-01-26

-- ============================================================================
-- Update collaboration_phase to include new phases
-- ============================================================================

-- Update the comment to reflect all phases
COMMENT ON COLUMN projects.collaboration_phase IS
'Consultant-centric collaboration phase: pre_discovery, discovery, validation, prototype, proposal, build, delivery';

-- ============================================================================
-- Pending Items Queue
-- Items from various sources (features, personas, etc.) needing client input
-- ============================================================================

CREATE TYPE pending_item_type AS ENUM (
    'feature',
    'persona',
    'vp_step',
    'question',
    'document',
    'kpi',
    'goal',
    'pain_point',
    'requirement'
);

CREATE TYPE pending_item_source AS ENUM (
    'phase_workflow',   -- Part of current phase workflow
    'needs_review',     -- Marked "needs review" from Features/Personas/etc.
    'ai_generated',     -- AI suggested this needs input
    'manual'            -- Consultant added manually
);

CREATE TABLE pending_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Item identification
    item_type pending_item_type NOT NULL,
    source pending_item_source NOT NULL DEFAULT 'manual',
    entity_id UUID,  -- ID of the feature/persona/etc. (nullable for questions/docs)

    -- Content
    title TEXT NOT NULL,
    description TEXT,
    why_needed TEXT,  -- "Helps us understand workflow"

    -- Prioritization
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),

    -- Tracking
    added_by TEXT,  -- "AI", "Consultant name", "Phase workflow"

    -- Status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_package', 'sent', 'resolved')),
    resolved_at TIMESTAMPTZ,
    resolved_by UUID,

    -- Package association (when included in a package)
    package_id UUID,  -- Set when added to a package

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_pending_items_project ON pending_items(project_id);
CREATE INDEX idx_pending_items_status ON pending_items(project_id, status);
CREATE INDEX idx_pending_items_type ON pending_items(project_id, item_type);
CREATE INDEX idx_pending_items_entity ON pending_items(entity_id) WHERE entity_id IS NOT NULL;

CREATE TRIGGER update_pending_items_updated_at
    BEFORE UPDATE ON pending_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Client Packages
-- AI-synthesized packages of questions/action items for clients
-- ============================================================================

CREATE TYPE package_status AS ENUM (
    'draft',              -- Being edited by consultant
    'ready',              -- Ready to send
    'sent',               -- Sent to portal
    'partial_response',   -- Some responses received
    'complete'            -- All responses received
);

CREATE TABLE client_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Status
    status package_status NOT NULL DEFAULT 'draft',

    -- Counts (denormalized for quick access)
    questions_count INT DEFAULT 0,
    action_items_count INT DEFAULT 0,
    suggestions_count INT DEFAULT 0,
    source_items_count INT DEFAULT 0,

    -- Response tracking
    questions_answered INT DEFAULT 0,
    action_items_completed INT DEFAULT 0,

    -- AI synthesis metadata
    synthesis_notes TEXT,  -- AI explanation of synthesis choices

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_client_packages_project ON client_packages(project_id);
CREATE INDEX idx_client_packages_status ON client_packages(project_id, status);

CREATE TRIGGER update_client_packages_updated_at
    BEFORE UPDATE ON client_packages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Package Questions
-- AI-synthesized questions within a package
-- ============================================================================

CREATE TABLE package_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL REFERENCES client_packages(id) ON DELETE CASCADE,

    -- Content
    question_text TEXT NOT NULL,
    hint TEXT,                    -- "Think about tools, handoffs, pain points"
    suggested_answerer TEXT,      -- "Product Owner, Requirements Lead"
    why_asking TEXT,              -- "Helps us understand your workflow"
    example_answer TEXT,

    -- Coverage tracking
    covers_items UUID[] DEFAULT '{}',  -- IDs of pending items this covers
    covers_summary TEXT,               -- "Covers: 2 features, 1 persona"

    -- Ordering
    sequence_order INT NOT NULL DEFAULT 0,

    -- Response
    answer_text TEXT,
    answered_by UUID,
    answered_by_name TEXT,
    answered_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_package_questions_package ON package_questions(package_id);
CREATE INDEX idx_package_questions_order ON package_questions(package_id, sequence_order);

CREATE TRIGGER update_package_questions_updated_at
    BEFORE UPDATE ON package_questions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Package Action Items
-- Documents to upload, tasks to complete
-- ============================================================================

CREATE TABLE package_action_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL REFERENCES client_packages(id) ON DELETE CASCADE,

    -- Content
    title TEXT NOT NULL,
    description TEXT,
    item_type TEXT DEFAULT 'document' CHECK (item_type IN ('document', 'task', 'approval')),
    hint TEXT,                    -- "Screenshots work great"
    why_needed TEXT,              -- "Helps us model your data structure"

    -- Coverage tracking
    covers_items UUID[] DEFAULT '{}',

    -- Ordering
    sequence_order INT NOT NULL DEFAULT 0,

    -- Completion
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'complete', 'skipped')),
    completed_by UUID,
    completed_at TIMESTAMPTZ,
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_package_action_items_package ON package_action_items(package_id);
CREATE INDEX idx_package_action_items_status ON package_action_items(package_id, status);

CREATE TRIGGER update_package_action_items_updated_at
    BEFORE UPDATE ON package_action_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Package Asset Suggestions
-- AI-suggested assets that would provide high inference value
-- ============================================================================

CREATE TABLE package_asset_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL REFERENCES client_packages(id) ON DELETE CASCADE,

    -- Content
    category TEXT NOT NULL CHECK (category IN ('sample_data', 'process', 'data_systems', 'integration')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    why_valuable TEXT NOT NULL,   -- "Lets us model your exact data entities"
    examples TEXT[] DEFAULT '{}', -- ["CSV export", "JSON file"]
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),

    -- Phase relevance
    phase_relevant TEXT[] DEFAULT '{}',  -- ["pre_discovery", "prototype"]

    -- Client response
    included BOOLEAN DEFAULT false,  -- Whether client chose to include this
    uploaded_file_ids UUID[] DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_package_asset_suggestions_package ON package_asset_suggestions(package_id);

-- ============================================================================
-- Uploaded Files for Action Items
-- Files uploaded by clients in response to action items
-- ============================================================================

CREATE TABLE package_uploaded_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_item_id UUID NOT NULL REFERENCES package_action_items(id) ON DELETE CASCADE,
    package_id UUID NOT NULL REFERENCES client_packages(id) ON DELETE CASCADE,

    -- File info
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,  -- Storage path
    file_size INT,
    file_type TEXT,
    mime_type TEXT,

    -- Uploader
    uploaded_by UUID NOT NULL,
    uploaded_by_name TEXT,

    -- Processing
    processed BOOLEAN DEFAULT false,
    signal_id UUID,  -- If converted to a signal

    -- Timestamps
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_package_uploaded_files_action_item ON package_uploaded_files(action_item_id);
CREATE INDEX idx_package_uploaded_files_package ON package_uploaded_files(package_id);

-- ============================================================================
-- Update pending_items foreign key
-- ============================================================================

ALTER TABLE pending_items
ADD CONSTRAINT fk_pending_items_package
FOREIGN KEY (package_id) REFERENCES client_packages(id) ON DELETE SET NULL;

-- ============================================================================
-- RLS Policies
-- ============================================================================

ALTER TABLE pending_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE package_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE package_action_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE package_asset_suggestions ENABLE ROW LEVEL SECURITY;
ALTER TABLE package_uploaded_files ENABLE ROW LEVEL SECURITY;

-- Consultants can manage all
CREATE POLICY "Consultants can manage pending_items"
ON pending_items FOR ALL TO authenticated
USING (project_id IN (
    SELECT project_id FROM project_members
    WHERE user_id = auth.uid() AND role IN ('owner', 'consultant', 'admin')
));

CREATE POLICY "Consultants can manage client_packages"
ON client_packages FOR ALL TO authenticated
USING (project_id IN (
    SELECT project_id FROM project_members
    WHERE user_id = auth.uid() AND role IN ('owner', 'consultant', 'admin')
));

CREATE POLICY "Consultants can manage package_questions"
ON package_questions FOR ALL TO authenticated
USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = auth.uid() AND pm.role IN ('owner', 'consultant', 'admin')
));

CREATE POLICY "Consultants can manage package_action_items"
ON package_action_items FOR ALL TO authenticated
USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = auth.uid() AND pm.role IN ('owner', 'consultant', 'admin')
));

CREATE POLICY "Consultants can manage package_asset_suggestions"
ON package_asset_suggestions FOR ALL TO authenticated
USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = auth.uid() AND pm.role IN ('owner', 'consultant', 'admin')
));

CREATE POLICY "Consultants can manage package_uploaded_files"
ON package_uploaded_files FOR ALL TO authenticated
USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = auth.uid() AND pm.role IN ('owner', 'consultant', 'admin')
));

-- Clients can view and respond to their packages
CREATE POLICY "Clients can view sent packages"
ON client_packages FOR SELECT TO authenticated
USING (
    status IN ('sent', 'partial_response', 'complete')
    AND project_id IN (
        SELECT project_id FROM project_members
        WHERE user_id = auth.uid() AND role = 'client'
    )
);

CREATE POLICY "Clients can view questions in sent packages"
ON package_questions FOR SELECT TO authenticated
USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = auth.uid() AND pm.role = 'client'
    AND cp.status IN ('sent', 'partial_response', 'complete')
));

CREATE POLICY "Clients can answer questions"
ON package_questions FOR UPDATE TO authenticated
USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = auth.uid() AND pm.role = 'client'
    AND cp.status IN ('sent', 'partial_response')
));

CREATE POLICY "Clients can view action items in sent packages"
ON package_action_items FOR SELECT TO authenticated
USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = auth.uid() AND pm.role = 'client'
    AND cp.status IN ('sent', 'partial_response', 'complete')
));

CREATE POLICY "Clients can complete action items"
ON package_action_items FOR UPDATE TO authenticated
USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = auth.uid() AND pm.role = 'client'
    AND cp.status IN ('sent', 'partial_response')
));

CREATE POLICY "Clients can upload files"
ON package_uploaded_files FOR INSERT TO authenticated
WITH CHECK (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = auth.uid() AND pm.role = 'client'
    AND cp.status IN ('sent', 'partial_response')
));

CREATE POLICY "Clients can view asset suggestions"
ON package_asset_suggestions FOR SELECT TO authenticated
USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = auth.uid() AND pm.role = 'client'
    AND cp.status IN ('sent', 'partial_response', 'complete')
));

-- ============================================================================
-- Helper function to update package response counts
-- ============================================================================

CREATE OR REPLACE FUNCTION update_package_response_counts()
RETURNS TRIGGER AS $$
BEGIN
    -- Update counts on the package
    UPDATE client_packages SET
        questions_answered = (
            SELECT COUNT(*) FROM package_questions
            WHERE package_id = NEW.package_id AND answer_text IS NOT NULL
        ),
        action_items_completed = (
            SELECT COUNT(*) FROM package_action_items
            WHERE package_id = NEW.package_id AND status = 'complete'
        ),
        status = CASE
            WHEN (
                SELECT COUNT(*) FROM package_questions WHERE package_id = NEW.package_id AND answer_text IS NOT NULL
            ) = questions_count
            AND (
                SELECT COUNT(*) FROM package_action_items WHERE package_id = NEW.package_id AND status = 'complete'
            ) = action_items_count
            THEN 'complete'::package_status
            WHEN (
                SELECT COUNT(*) FROM package_questions WHERE package_id = NEW.package_id AND answer_text IS NOT NULL
            ) > 0
            OR (
                SELECT COUNT(*) FROM package_action_items WHERE package_id = NEW.package_id AND status = 'complete'
            ) > 0
            THEN 'partial_response'::package_status
            ELSE status
        END,
        updated_at = now()
    WHERE id = NEW.package_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on questions
CREATE TRIGGER trigger_update_package_counts_on_question
    AFTER UPDATE OF answer_text ON package_questions
    FOR EACH ROW
    WHEN (NEW.answer_text IS DISTINCT FROM OLD.answer_text)
    EXECUTE FUNCTION update_package_response_counts();

-- Trigger on action items
CREATE TRIGGER trigger_update_package_counts_on_action_item
    AFTER UPDATE OF status ON package_action_items
    FOR EACH ROW
    WHEN (NEW.status IS DISTINCT FROM OLD.status)
    EXECUTE FUNCTION update_package_response_counts();
