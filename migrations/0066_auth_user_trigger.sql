-- Migration: 0066_auth_user_trigger.sql
-- Description: Auto-create user, profile, and organization when auth user is created
-- Date: 2026-01-14

-- ============================================================================
-- Function to handle new auth user signup
-- Differentiates between consultants (invited via consultant_invites) and clients
-- ============================================================================
CREATE OR REPLACE FUNCTION handle_new_auth_user()
RETURNS TRIGGER AS $$
DECLARE
  user_first_name TEXT;
  user_last_name TEXT;
  user_email TEXT;
  org_name TEXT;
  new_org_id UUID;
  is_consultant BOOLEAN := FALSE;
  invite_record RECORD;
BEGIN
  -- Extract user info from auth.users
  user_email := LOWER(NEW.email);
  user_first_name := COALESCE(
    NEW.raw_user_meta_data->>'first_name',
    split_part(NEW.email, '@', 1)
  );
  user_last_name := COALESCE(
    NEW.raw_user_meta_data->>'last_name',
    ''
  );

  -- Check if this user was invited as a consultant
  SELECT * INTO invite_record
  FROM public.consultant_invites
  WHERE LOWER(email) = user_email
    AND status = 'pending'
  LIMIT 1;

  IF invite_record.id IS NOT NULL THEN
    is_consultant := TRUE;

    -- Mark the invite as accepted
    UPDATE public.consultant_invites
    SET status = 'accepted', accepted_at = NOW()
    WHERE id = invite_record.id;
  END IF;

  IF is_consultant THEN
    -- CONSULTANT FLOW: Create user, profile with invited role, org, and membership

    -- Create the users record
    INSERT INTO public.users (id, email, user_type, first_name, last_name, created_at, updated_at)
    VALUES (NEW.id, user_email, 'consultant', user_first_name, user_last_name, NOW(), NOW())
    ON CONFLICT (id) DO NOTHING;

    -- Create the profiles record with the role from the invite (or default to sales_consultant)
    INSERT INTO public.profiles (user_id, email, first_name, last_name, platform_role, created_at, updated_at)
    VALUES (NEW.id, user_email, user_first_name, user_last_name, COALESCE(invite_record.platform_role, 'sales_consultant'), NOW(), NOW())
    ON CONFLICT (user_id) DO NOTHING;

    -- Create organization named "{first_name}'s Organization"
    org_name := user_first_name || '''s Organization';

    INSERT INTO public.organizations (name, created_by_user_id, created_at, updated_at)
    VALUES (org_name, NEW.id, NOW(), NOW())
    RETURNING id INTO new_org_id;

    -- Add user as Owner of the organization
    INSERT INTO public.organization_members (organization_id, user_id, organization_role, invited_by_user_id, created_at, updated_at)
    VALUES (new_org_id, NEW.id, 'Owner', NEW.id, NOW(), NOW());

    -- If invite specified an org, also add them to that org as Member
    IF invite_record.organization_id IS NOT NULL THEN
      INSERT INTO public.organization_members (organization_id, user_id, organization_role, invited_by_user_id, created_at, updated_at)
      VALUES (invite_record.organization_id, NEW.id, 'Member', invite_record.invited_by, NOW(), NOW())
      ON CONFLICT (organization_id, user_id) DO NOTHING;
    END IF;

  ELSE
    -- CLIENT FLOW: Just create user record (no profile, no org)
    -- Clients get project access via project_members, not org membership

    INSERT INTO public.users (id, email, user_type, first_name, last_name, created_at, updated_at)
    VALUES (NEW.id, user_email, 'client', user_first_name, user_last_name, NOW(), NOW())
    ON CONFLICT (id) DO NOTHING;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- Trigger on auth.users insert
-- ============================================================================
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION handle_new_auth_user();

-- ============================================================================
-- Grant necessary permissions
-- ============================================================================
-- The function runs as SECURITY DEFINER so it has the permissions of the creator
-- But we need to ensure the authenticated role can trigger it
GRANT USAGE ON SCHEMA public TO postgres, authenticated, service_role;
