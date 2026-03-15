-- ============================================================
-- Bulk-create 29 team accounts for high school event
-- Run this in the Supabase SQL Editor (requires service_role access)
--
-- What this does:
--   1. Creates 29 auth users with email/password (email verified)
--   2. Creates auth.identities rows (required for signInWithPassword)
--   3. The handle_new_user trigger auto-creates profiles with 0 credits
--   4. Updates each profile to 3 credits + marks signup_bonus_granted
--   5. Logs credit transactions for audit trail
-- ============================================================

DO $$
DECLARE
  emails TEXT[] := ARRAY[
    'theroomoffour@maviriq.com',
    'deficitfix@maviriq.com',
    'liora@maviriq.com',
    'menininkai@maviriq.com',
    'rizikuotojai@maviriq.com',
    'kaimasvsmiestas@maviriq.com',
    'risciplex@maviriq.com',
    'yh@maviriq.com',
    'siaskes@maviriq.com',
    'komandanr10@maviriq.com',
    'ruoniai@maviriq.com',
    'komandanr12@maviriq.com',
    'futura@maviriq.com',
    'novax@maviriq.com',
    'contles@maviriq.com',
    'megejai@maviriq.com',
    'didysispenketas@maviriq.com',
    'egbv@maviriq.com',
    'apmu@maviriq.com',
    'antrepreneriai@maviriq.com',
    'ssend@maviriq.com',
    'raudonakibirkstis@maviriq.com',
    'futurefounders@maviriq.com',
    'verslininkai@maviriq.com',
    'verslorinktine@maviriq.com',
    'appsai@maviriq.com',
    'lietuvininkai@maviriq.com',
    'ownit@maviriq.com',
    'paprastiverslininkai@maviriq.com'
  ];
  passwords TEXT[] := ARRAY[
    'xK7mQ2vL9pNw',
    'bR4nW8tJ3yHs',
    'gT6kP1mX5cQz',
    'wN3hF9rD7vLx',
    'jY8sK4tB2mGn',
    'pL5wQ7cX1hRv',
    'dH2nT6yM9kFs',
    'vB9gJ3pW5tLx',
    'mR7cN1kH4yQw',
    'sX4tF8vL2gBn',
    'hK6wP3mJ9rDy',
    'tN1yR5gX7cLs',
    'qW8kB4hT2nMv',
    'fJ3pL7wD9sKx',
    'yH5mN2rG6tBc',
    'kX9vT1gQ4wFs',
    'nR6cJ8hL3yPm',
    'wT2kB5pX7gNs',
    'mH4rF9vJ1tLy',
    'cQ7nW3gK6hDx',
    'pY1sT8mR4bLv',
    'gN5kX2wH7cJt',
    'rB8vL4tQ9mFs',
    'hW3yP6gN1kDx',
    'tJ7mR2cX5vBs',
    'kL9hT4wF8nQy',
    'sG2pB6rJ3yMx',
    'vN5kW9tH1gLc',
    'xR8mF3cQ6wTs'
  ];
  i INT;
  new_user_id UUID;
BEGIN
  FOR i IN 1..array_length(emails, 1) LOOP
    new_user_id := gen_random_uuid();

    -- 1. Create auth user (email_confirmed_at = now() skips email verification)
    INSERT INTO auth.users (
      instance_id, id, aud, role, email,
      encrypted_password, email_confirmed_at,
      created_at, updated_at, confirmation_token,
      raw_app_meta_data, raw_user_meta_data
    ) VALUES (
      '00000000-0000-0000-0000-000000000000',
      new_user_id, 'authenticated', 'authenticated',
      emails[i],
      crypt(passwords[i], gen_salt('bf')),
      now(), now(), now(), '',
      '{"provider":"email","providers":["email"]}'::jsonb,
      '{}'::jsonb
    );

    -- 2. Create identity row (required for signInWithPassword to work)
    INSERT INTO auth.identities (
      id, user_id, identity_data, provider, provider_id,
      last_sign_in_at, created_at, updated_at
    ) VALUES (
      new_user_id, new_user_id,
      jsonb_build_object('sub', new_user_id::text, 'email', emails[i], 'email_verified', true),
      'email', new_user_id::text,
      now(), now(), now()
    );

    -- 3. handle_new_user trigger fires automatically here,
    --    creating a profiles row with 0 credits

    -- 4. Set 3 credits + mark signup bonus as granted (prevents extra bonus on first login)
    UPDATE public.profiles
    SET credits = 3, signup_bonus_granted = TRUE
    WHERE id = new_user_id;

    -- 5. Log credit transaction for audit trail
    INSERT INTO public.credit_transactions (id, user_id, amount, type)
    VALUES (
      'txn_' || substr(md5(random()::text), 1, 12),
      new_user_id, 3, 'event_provision'
    );
  END LOOP;

  RAISE NOTICE 'Successfully created % team accounts', array_length(emails, 1);
END;
$$;


-- ============================================================
-- Verification: run this after the script above to confirm
-- ============================================================
SELECT
  p.email,
  p.credits,
  p.signup_bonus_granted,
  ct.amount AS txn_amount,
  ct.type AS txn_type,
  p.created_at
FROM public.profiles p
LEFT JOIN public.credit_transactions ct ON ct.user_id = p.id
WHERE p.email LIKE '%@maviriq.com'
ORDER BY p.email;
