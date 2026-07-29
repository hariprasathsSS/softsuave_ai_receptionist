-- ============================================================================
-- AI Universal Receptionist — Database Initialization
-- Executed on first PostgreSQL start (pgvector image)
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- TENANT & SUBSCRIPTION
-- ============================================================================

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    email_domain VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    tier INT NOT NULL,
    max_domain_profiles INT DEFAULT 1,
    max_phone_numbers INT DEFAULT 1,
    included_call_minutes INT DEFAULT 1000,
    included_bookings INT DEFAULT 100,
    has_priority_support BOOLEAN DEFAULT false,
    overage_rate_per_minute DECIMAL(10,4) DEFAULT 0,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE tenant_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL UNIQUE REFERENCES tenants(id),
    plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    status VARCHAR(50) DEFAULT 'active',
    trial_ends_at TIMESTAMPTZ,
    current_period_start TIMESTAMPTZ NOT NULL DEFAULT now(),
    current_period_end TIMESTAMPTZ NOT NULL,
    call_minutes_used INT DEFAULT 0,
    bookings_used INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE tenant_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'tenant_operator',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, email)
);

CREATE TABLE phone_numbers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    domain_profile_id UUID UNIQUE,
    number VARCHAR(20) UNIQUE NOT NULL,
    twilio_sid VARCHAR(100) NOT NULL,
    country VARCHAR(2) DEFAULT 'US',
    is_active BOOLEAN DEFAULT true,
    provisioned_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- DOMAIN PROFILES & KNOWLEDGE BASE
-- ============================================================================

CREATE TABLE domain_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    organization_name VARCHAR(255) NOT NULL,
    greeting_template TEXT NOT NULL DEFAULT 'Hello, this is {organization}. How can I help?',
    voice_style VARCHAR(50) DEFAULT 'conversational',
    operating_hours JSONB NOT NULL DEFAULT '{}',
    timezone VARCHAR(50) DEFAULT 'UTC',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE faq_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_profile_id UUID NOT NULL REFERENCES domain_profiles(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    embedding vector(1536),
    category VARCHAR(100),
    priority INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true
);
CREATE INDEX idx_faq_embedding ON faq_entries USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE intent_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_profile_id UUID NOT NULL REFERENCES domain_profiles(id) ON DELETE CASCADE,
    intent_name VARCHAR(100) NOT NULL,
    display_label VARCHAR(255),
    training_examples TEXT[] NOT NULL DEFAULT '{}',
    required_slots JSONB DEFAULT '[]',
    response_template TEXT,
    priority INT DEFAULT 0
);

CREATE TABLE booking_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_profile_id UUID NOT NULL UNIQUE REFERENCES domain_profiles(id) ON DELETE CASCADE,
    resource_type VARCHAR(100) NOT NULL,
    slot_duration_minutes INT DEFAULT 30,
    buffer_minutes INT DEFAULT 5,
    confirmation_template TEXT
);

CREATE TABLE escalation_routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_profile_id UUID NOT NULL REFERENCES domain_profiles(id) ON DELETE CASCADE,
    target_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(50) NOT NULL,
    intent_triggers TEXT[] DEFAULT '{}',
    urgency_threshold VARCHAR(20) DEFAULT 'urgent',
    fallback_behavior VARCHAR(50) DEFAULT 'voicemail'
);

CREATE TABLE notification_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_profile_id UUID NOT NULL REFERENCES domain_profiles(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    channel VARCHAR(20) NOT NULL DEFAULT 'sms',
    template_body TEXT NOT NULL,
    reminder_lead_minutes INT,
    is_active BOOLEAN DEFAULT true
);

-- ============================================================================
-- BOOKINGS & CALENDAR
-- ============================================================================

CREATE TABLE tenant_calendar_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL UNIQUE REFERENCES tenants(id),
    google_refresh_token_enc BYTEA,
    calendar_id VARCHAR(255) NOT NULL,
    slot_duration_minutes INT DEFAULT 30,
    buffer_minutes INT DEFAULT 5,
    is_connected BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    domain_profile_id UUID NOT NULL REFERENCES domain_profiles(id),
    resource_type VARCHAR(100) NOT NULL,
    resource_name VARCHAR(255) NOT NULL,
    calendar_event_id VARCHAR(255),
    caller_name VARCHAR(255) NOT NULL,
    caller_phone VARCHAR(50) NOT NULL,
    caller_email VARCHAR(255),
    slot_start TIMESTAMPTZ NOT NULL,
    slot_end TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) DEFAULT 'confirmed',
    notes TEXT,
    call_sid VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_resource_slot UNIQUE (tenant_id, resource_name, slot_start)
);
CREATE INDEX idx_bookings_tenant ON bookings(tenant_id, slot_start);
CREATE INDEX idx_bookings_caller ON bookings(tenant_id, caller_phone);

-- ============================================================================
-- CALL LOGS & RECORDINGS
-- ============================================================================

CREATE TABLE call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    domain_profile_id UUID REFERENCES domain_profiles(id),
    call_sid VARCHAR(100) UNIQUE NOT NULL,
    caller_number_hash VARCHAR(64) NOT NULL,
    caller_name VARCHAR(255),
    language VARCHAR(10) DEFAULT 'en',
    intents_detected JSONB DEFAULT '[]',
    actions_taken JSONB DEFAULT '[]',
    outcome VARCHAR(50) DEFAULT 'in_progress',
    sentiment_summary JSONB DEFAULT '{}',
    duration_seconds INT DEFAULT 0,
    recording_url TEXT,
    transcript_text TEXT,
    transcript_json JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_call_logs_tenant ON call_logs(tenant_id, created_at DESC);
CREATE INDEX idx_call_logs_domain ON call_logs(domain_profile_id, created_at DESC);

-- ============================================================================
-- CALLER PROFILES
-- ============================================================================

CREATE TABLE caller_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    phone_number_hash VARCHAR(64) NOT NULL,
    name VARCHAR(255),
    preferred_language VARCHAR(10) DEFAULT 'en',
    is_vip BOOLEAN DEFAULT false,
    last_interaction_at TIMESTAMPTZ,
    total_calls INT DEFAULT 0,
    total_bookings INT DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, phone_number_hash)
);

-- ============================================================================
-- WAITLIST
-- ============================================================================

CREATE TABLE waitlist_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    domain_profile_id UUID NOT NULL REFERENCES domain_profiles(id),
    resource_name VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    caller_name VARCHAR(255) NOT NULL,
    caller_phone VARCHAR(50) NOT NULL,
    preferred_date DATE,
    preferred_window JSONB,
    status VARCHAR(50) DEFAULT 'waiting',
    notified_at TIMESTAMPTZ,
    booking_id UUID REFERENCES bookings(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- OUTBOUND CALLS
-- ============================================================================

CREATE TABLE outbound_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    call_type VARCHAR(50) NOT NULL,
    to_phone VARCHAR(50) NOT NULL,
    message_template TEXT NOT NULL,
    context_json JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    call_sid VARCHAR(100),
    scheduled_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- ROW-LEVEL SECURITY (Phase 5 — uncomment when tenant middleware is active)
-- ============================================================================

-- ALTER TABLE domain_profiles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE faq_entries ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE call_logs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE caller_profiles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE waitlist_entries ENABLE ROW LEVEL SECURITY;

-- CREATE POLICY tenant_isolation ON domain_profiles
--     FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- ============================================================================
-- SEED DATA: Default subscription plans
-- ============================================================================

INSERT INTO subscription_plans (name, tier, max_domain_profiles, max_phone_numbers, included_call_minutes, included_bookings, has_priority_support, overage_rate_per_minute) VALUES
    ('Starter', 1, 1, 1, 1000, 100, false, 0.05),
    ('Growth', 2, 5, 5, 5000, 500, true, 0.03),
    ('Enterprise', 3, 100, 100, 50000, 5000, true, 0.01);
