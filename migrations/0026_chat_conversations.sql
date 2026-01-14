-- Migration: Chat Conversations and Messages
-- Description: Add tables for persisting chat conversations and messages
-- Author: Phase 2 - Chat Assistant
-- Date: 2024-12-29

-- ============================================================================
-- Conversations Table
-- ============================================================================
-- Stores conversation metadata and history

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT, -- Auto-generated from first message or user-provided
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ, -- For sorting by recent activity
    message_count INT DEFAULT 0, -- Cached count for performance
    is_archived BOOLEAN DEFAULT FALSE,

    -- Indexes
    CONSTRAINT conversations_project_id_fkey FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS conversations_project_id_idx ON conversations(project_id);
CREATE INDEX IF NOT EXISTS conversations_updated_at_idx ON conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS conversations_last_message_at_idx ON conversations(last_message_at DESC);

-- ============================================================================
-- Messages Table
-- ============================================================================
-- Stores individual messages within conversations

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Tool execution tracking
    tool_calls JSONB, -- Array of {tool_name, status, result}

    -- Metadata
    metadata JSONB, -- For future extensibility (e.g., model version, tokens used)

    -- Indexes
    CONSTRAINT messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS messages_conversation_id_idx ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS messages_created_at_idx ON messages(created_at);

-- ============================================================================
-- Triggers
-- ============================================================================

-- Update conversations.updated_at on message insert
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

CREATE TRIGGER messages_update_conversation_timestamp
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_timestamp();

-- Auto-generate conversation title from first user message
CREATE OR REPLACE FUNCTION auto_title_conversation()
RETURNS TRIGGER AS $$
DECLARE
    conv_title TEXT;
BEGIN
    -- Only set title if it's null and this is a user message
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
