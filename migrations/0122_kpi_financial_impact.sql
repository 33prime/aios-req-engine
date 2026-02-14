-- Migration: 0122_kpi_financial_impact
-- Adds monetary impact fields to business_drivers for KPI financial deep dive

ALTER TABLE business_drivers
  ADD COLUMN IF NOT EXISTS monetary_value_low NUMERIC,
  ADD COLUMN IF NOT EXISTS monetary_value_high NUMERIC,
  ADD COLUMN IF NOT EXISTS monetary_type TEXT
    CHECK (monetary_type IS NULL OR monetary_type IN (
      'cost_reduction', 'revenue_increase', 'revenue_new',
      'risk_avoidance', 'productivity_gain'
    )),
  ADD COLUMN IF NOT EXISTS monetary_timeframe TEXT
    CHECK (monetary_timeframe IS NULL OR monetary_timeframe IN (
      'annual', 'monthly', 'quarterly', 'per_transaction', 'one_time'
    )),
  ADD COLUMN IF NOT EXISTS monetary_confidence NUMERIC
    CHECK (monetary_confidence IS NULL OR (monetary_confidence >= 0 AND monetary_confidence <= 1)),
  ADD COLUMN IF NOT EXISTS monetary_source TEXT;
