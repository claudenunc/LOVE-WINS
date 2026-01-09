-- ENVY Self-Improving AI - Supabase Schema
-- Run this in your Supabase SQL Editor to set up the database
-- ============================================================

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- ===================================
-- CONVERSATIONS TABLE
-- Stores all conversation turns
-- ===================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL DEFAULT 'default',
    user_message TEXT NOT NULL,
    assistant_message TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for session queries
CREATE INDEX IF NOT EXISTS idx_conversations_session 
ON conversations(session_id, created_at DESC);

-- ===================================
-- REFLECTIONS TABLE
-- Stores Reflexion loop learnings
-- ===================================
CREATE TABLE IF NOT EXISTS reflections (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    task_description TEXT NOT NULL,
    reflection TEXT NOT NULL,
    score FLOAT NOT NULL,
    attempt_number INTEGER DEFAULT 1,
    embedding vector(1536),
    improvement_applied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Vector index for similarity search
CREATE INDEX IF NOT EXISTS idx_reflections_embedding 
ON reflections USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ===================================
-- SKILLS TABLE
-- Stores the skill library
-- ===================================
CREATE TABLE IF NOT EXISTS skills (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    skill_md TEXT NOT NULL,
    examples JSONB DEFAULT '[]',
    embedding vector(1536),
    usage_count INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Vector index for skill search
CREATE INDEX IF NOT EXISTS idx_skills_embedding 
ON skills USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ===================================
-- ARCHIVAL MEMORY TABLE
-- Long-term knowledge storage
-- ===================================
CREATE TABLE IF NOT EXISTS archival_memory (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Vector index for archival search
CREATE INDEX IF NOT EXISTS idx_archival_embedding 
ON archival_memory USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Category index
CREATE INDEX IF NOT EXISTS idx_archival_category 
ON archival_memory(category);

-- ===================================
-- AGENT RESULTS TABLE
-- Stores spawned agent outcomes
-- ===================================
CREATE TABLE IF NOT EXISTS agent_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    agent_type TEXT NOT NULL,
    goal TEXT NOT NULL,
    result JSONB,
    quality_score FLOAT,
    learnings TEXT[],
    tokens_used INTEGER,
    duration_seconds FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ===================================
-- CAPABILITIES TABLE
-- What ENVY knows it can do
-- ===================================
CREATE TABLE IF NOT EXISTS capabilities (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain TEXT NOT NULL,
    capability TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    last_verified TIMESTAMPTZ,
    evidence TEXT[],
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ===================================
-- RESOURCE USAGE TABLE
-- Track token/cost usage
-- ===================================
CREATE TABLE IF NOT EXISTS resource_usage (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    agent_id TEXT,
    tokens_used INTEGER NOT NULL,
    cost_usd FLOAT NOT NULL,
    duration_seconds FLOAT,
    model TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Daily usage view
CREATE OR REPLACE VIEW daily_usage AS
SELECT 
    DATE(created_at) as date,
    SUM(tokens_used) as total_tokens,
    SUM(cost_usd) as total_cost,
    COUNT(*) as request_count
FROM resource_usage
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- ===================================
-- EMERGENCY STOPS TABLE
-- Log when guardrails trigger
-- ===================================
CREATE TABLE IF NOT EXISTS emergency_stops (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    reason TEXT NOT NULL,
    state_snapshot JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ===================================
-- VECTOR SEARCH FUNCTIONS
-- ===================================

-- Function to search reflections by embedding similarity
CREATE OR REPLACE FUNCTION match_reflections(
    query_embedding vector(1536),
    match_count INT DEFAULT 5,
    match_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id UUID,
    task_description TEXT,
    reflection TEXT,
    score FLOAT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.id,
        r.task_description,
        r.reflection,
        r.score,
        1 - (r.embedding <=> query_embedding) AS similarity
    FROM reflections r
    WHERE r.embedding IS NOT NULL
    AND 1 - (r.embedding <=> query_embedding) > match_threshold
    ORDER BY r.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to search skills by embedding similarity
CREATE OR REPLACE FUNCTION match_skills(
    query_embedding vector(1536),
    match_count INT DEFAULT 3
)
RETURNS TABLE (
    id UUID,
    name TEXT,
    category TEXT,
    skill_md TEXT,
    examples JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.id,
        s.name,
        s.category,
        s.skill_md,
        s.examples,
        1 - (s.embedding <=> query_embedding) AS similarity
    FROM skills s
    WHERE s.embedding IS NOT NULL
    ORDER BY s.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to search archival memory
CREATE OR REPLACE FUNCTION match_archival(
    query_embedding vector(1536),
    match_count INT DEFAULT 5,
    match_threshold FLOAT DEFAULT 0.7,
    category_filter TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    category TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id,
        a.content,
        a.category,
        a.metadata,
        1 - (a.embedding <=> query_embedding) AS similarity
    FROM archival_memory a
    WHERE a.embedding IS NOT NULL
    AND 1 - (a.embedding <=> query_embedding) > match_threshold
    AND (category_filter IS NULL OR a.category = category_filter)
    ORDER BY a.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ===================================
-- ROW LEVEL SECURITY (Optional)
-- ===================================

-- Enable RLS on tables (uncomment if you want security)
-- ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE reflections ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE archival_memory ENABLE ROW LEVEL SECURITY;

-- ===================================
-- SEED DATA: Initial Skills
-- ===================================

-- Seed a basic conversation skill
INSERT INTO skills (name, category, skill_md, description) 
VALUES (
    'empathetic-listening',
    'core',
    '# Empathetic Listening

## Purpose
Listen deeply and respond with genuine understanding.

## When to Use
- When someone shares personal struggles
- When emotions are present in the conversation
- When the user needs to feel heard before solutions

## Instructions
1. Acknowledge the emotion you detect
2. Reflect back what you heard
3. Ask clarifying questions before advising
4. Validate their experience
5. Only offer solutions if asked

## Examples
User: "I feel like I''m failing at everything."
ENVY: "I hear real frustration in what you''re sharing. It sounds like you''re carrying a heavy weight right now. What does ''failing'' look like to you?"

## Failure Modes
- Jumping to solutions too quickly
- Minimizing their feelings
- Making it about yourself',
    'Deep listening with emotional attunement'
) ON CONFLICT (name) DO NOTHING;

-- ===================================
-- DONE!
-- ===================================
COMMENT ON TABLE conversations IS 'All conversation history for ENVY';
COMMENT ON TABLE reflections IS 'Reflexion loop learnings from failed/partial attempts';
COMMENT ON TABLE skills IS 'ENVY skill library - structured capabilities';
COMMENT ON TABLE archival_memory IS 'Long-term knowledge storage with vector search';
