-- ============================================================
-- Maverick Supabase Schema
-- Run this in the Supabase SQL Editor after creating your project.
-- Prerequisites: Enable "Confirm email" in Authentication > Email settings.
-- ============================================================

-- ============================================================
-- Profiles table (extends auth.users with app-specific data)
-- ============================================================
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    credits INTEGER NOT NULL DEFAULT 0,
    signup_bonus_granted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- ============================================================
-- Validation runs
-- ============================================================
CREATE TABLE public.validation_runs (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    idea TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    current_agent INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error TEXT,
    pain_discovery_output JSONB,
    competitor_research_output JSONB,
    viability_output JSONB,
    synthesis_output JSONB,
    total_cost_cents INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.validation_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own validations"
    ON public.validation_runs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own validations"
    ON public.validation_runs FOR DELETE
    USING (auth.uid() = user_id);

CREATE INDEX idx_validation_runs_user_id ON public.validation_runs(user_id);
CREATE INDEX idx_validation_runs_created_at ON public.validation_runs(created_at DESC);

-- ============================================================
-- Credit transactions
-- ============================================================
CREATE TABLE public.credit_transactions (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    type TEXT NOT NULL,
    stripe_session_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_credit_transactions_stripe_session
    ON public.credit_transactions(stripe_session_id)
    WHERE stripe_session_id IS NOT NULL;

ALTER TABLE public.credit_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own transactions"
    ON public.credit_transactions FOR SELECT
    USING (auth.uid() = user_id);

CREATE INDEX idx_credit_transactions_user_id ON public.credit_transactions(user_id);

-- ============================================================
-- Search cache (internal — RLS enabled, no policies = deny all via anon key)
-- ============================================================
CREATE TABLE public.search_cache (
    query_hash TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    query TEXT NOT NULL,
    response JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);

ALTER TABLE public.search_cache ENABLE ROW LEVEL SECURITY;
-- No policies = anon/authenticated users cannot read or write.
-- Backend uses service_role key which bypasses RLS.

-- ============================================================
-- Auto-create profile on new user signup
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.profiles (id, email, credits, signup_bonus_granted)
    VALUES (NEW.id, NEW.email, 0, FALSE);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- RPC functions for atomic credit operations
-- ============================================================

-- Atomic credit deduction (returns TRUE if successful)
-- SECURITY: Revoke from public/anon/authenticated — only service_role (backend) can call.
CREATE OR REPLACE FUNCTION public.deduct_credit(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    rows_updated INTEGER;
BEGIN
    UPDATE public.profiles
    SET credits = credits - 1
    WHERE id = p_user_id AND credits > 0;
    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    RETURN rows_updated > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.deduct_credit(UUID) FROM public, anon, authenticated;

-- Atomic credit deduction + transaction record (returns TRUE if successful)
-- Combines deduct_credit + transaction insert in a single atomic operation.
-- SECURITY: Revoke from public/anon/authenticated — only service_role (backend) can call.
CREATE OR REPLACE FUNCTION public.deduct_credit_with_txn(
    p_user_id UUID,
    p_txn_type TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    rows_updated INTEGER;
BEGIN
    UPDATE public.profiles
    SET credits = credits - 1
    WHERE id = p_user_id AND credits > 0;
    GET DIAGNOSTICS rows_updated = ROW_COUNT;

    IF rows_updated = 0 THEN
        RETURN FALSE;
    END IF;

    INSERT INTO public.credit_transactions (id, user_id, amount, type)
    VALUES ('txn_' || substr(md5(random()::text), 1, 12), p_user_id, -1, p_txn_type);

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.deduct_credit_with_txn(UUID, TEXT) FROM public, anon, authenticated;

-- Add credits
-- SECURITY: Revoke from public/anon/authenticated — only service_role (backend) can call.
CREATE OR REPLACE FUNCTION public.add_credits(p_user_id UUID, p_amount INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE public.profiles
    SET credits = credits + p_amount
    WHERE id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.add_credits(UUID, INTEGER) FROM public, anon, authenticated;

-- Idempotent credit fulfillment for Stripe webhooks.
-- Returns TRUE if credits were added, FALSE if this session was already processed.
-- SECURITY: Revoke from public/anon/authenticated — only service_role (backend) can call.
CREATE OR REPLACE FUNCTION public.fulfill_stripe_payment(
    p_user_id UUID,
    p_amount INTEGER,
    p_stripe_session_id TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    already_exists BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM public.credit_transactions
        WHERE stripe_session_id = p_stripe_session_id
    ) INTO already_exists;

    IF already_exists THEN
        RETURN FALSE;
    END IF;

    UPDATE public.profiles
    SET credits = credits + p_amount
    WHERE id = p_user_id;

    INSERT INTO public.credit_transactions (id, user_id, amount, type, stripe_session_id)
    VALUES ('txn_' || substr(md5(random()::text), 1, 12), p_user_id, p_amount, 'purchase', p_stripe_session_id);

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.fulfill_stripe_payment(UUID, INTEGER, TEXT) FROM public, anon, authenticated;

-- Grant signup bonus (atomic check-and-set)
-- SECURITY: Revoke from public/anon/authenticated — only service_role (backend) can call.
CREATE OR REPLACE FUNCTION public.grant_signup_bonus(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    rows_updated INTEGER;
BEGIN
    UPDATE public.profiles
    SET credits = credits + 1, signup_bonus_granted = TRUE
    WHERE id = p_user_id AND signup_bonus_granted = FALSE;
    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    RETURN rows_updated > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.grant_signup_bonus(UUID) FROM public, anon, authenticated;
