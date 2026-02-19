-- Migration: 0141_enable_realtime.sql
-- Enable Supabase Realtime (Postgres Changes) for entity tables.
-- Realtime respects RLS — events are filtered per-user automatically.

ALTER PUBLICATION supabase_realtime ADD TABLE features;
ALTER PUBLICATION supabase_realtime ADD TABLE personas;
ALTER PUBLICATION supabase_realtime ADD TABLE vp_steps;
ALTER PUBLICATION supabase_realtime ADD TABLE workflows;
ALTER PUBLICATION supabase_realtime ADD TABLE business_drivers;
ALTER PUBLICATION supabase_realtime ADD TABLE constraints;
ALTER PUBLICATION supabase_realtime ADD TABLE data_entities;
ALTER PUBLICATION supabase_realtime ADD TABLE stakeholders;
ALTER PUBLICATION supabase_realtime ADD TABLE competitor_references;
ALTER PUBLICATION supabase_realtime ADD TABLE pending_items;
ALTER PUBLICATION supabase_realtime ADD TABLE company_info;
ALTER PUBLICATION supabase_realtime ADD TABLE projects;
