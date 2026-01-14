-- Migration: Chat Conversations and Messages (Safe Version)
-- Description: Add tables for persisting chat conversations and messages
-- Handles existing objects gracefully
-- Author: Phase 2 - Chat Assistant
-- Date: 2024-12-29

-- ============================================================================
-- Conversations Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    message_count INT DEFAULT 0,
    is_archived BOOLEAN DEFAULT FALSE
);

-- Add foreign key only if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'conversations_project_id_fkey'
    ) THEN
        ALTER TABLE conversations
        ADD CONSTRAINT conversations_project_id_fkey
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Create indexes only if they don't exist
CREATE INDEX IF NOT EXISTS conversations_project_id_idx ON conversations(project_id);
CREATE INDEX IF NOT EXISTS conversations_updated_at_idx ON conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS conversations_last_message_at_idx ON conversations(last_message_at DESC);

-- ============================================================================
-- Messages Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tool_calls JSONB,
    metadata JSONB
);

-- Add foreign key only if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'messages_conversation_id_fkey'
    ) THEN
        ALTER TABLE messages
        ADD CONSTRAINT messages_conversation_id_fkey
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Create indexes only if they don't exist
CREATE INDEX IF NOT EXISTS messages_conversation_id_idx ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS messages_created_at_idx ON messages(created_at);

-- ============================================================================
-- Triggers
-- ============================================================================

-- Create trigger function for updating conversation timestamp
CREATE OR REPLACE FUNCTION update_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET
        updated_at = NOW(),
        last_message_at = NOW(),
        message_count = message_count + 1
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists, then recreate
DROP TRIGGER IF EXISTS messages_update_conversation_timestamp ON messages;
CREATE TRIGGER messages_update_conversation_timestamp
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_timestamp();

-- Create trigger function for auto-titling conversations
CREATE OR REPLACE FUNCTION auto_title_conversation()
RETURNS TRIGGER AS $$
DECLARE
    conv_title TEXT;
BEGIN
    IF NEW.role = 'user' THEN
        SELECT title INTO conv_title FROM conversations WHERE id = NEW.conversation_id;

        IF conv_title IS NULL THEN
            UPDATE conversations
            SET title = LEFT(NEW.content, 50) || CASE WHEN LENGTH(NEW.content) > 50 THEN '...' ELSE '' END
            WHERE id = NEW.conversation_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists, then recreate
DROP TRIGGER IF EXISTS messages_auto_title_conversation ON messages;
CREATE TRIGGER messages_auto_title_conversation
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION auto_title_conversation();

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE conversations IS 'Chat conversations with AI assistant, scoped to projects';
COMMENT ON TABLE messages IS 'Individual messages within conversations';
COMMENT ON COLUMN conversations.title IS 'Auto-generated from first message or user-provided';
COMMENT ON COLUMN conversations.last_message_at IS 'Timestamp of last message for sorting';
COMMENT ON COLUMN conversations.message_count IS 'Cached count for performance';
COMMENT ON COLUMN messages.tool_calls IS 'JSON array of tool executions: [{tool_name, status, result}]';
COMMENT ON COLUMN messages.metadata IS 'Extensible metadata (model version, tokens, etc.)';

-- ============================================================================
-- Success Message
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Chat conversations migration completed successfully!';
END $$;
