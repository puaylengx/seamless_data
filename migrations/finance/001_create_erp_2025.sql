-- migration: 001_create_erp_2025
-- table: erp_2025

CREATE TABLE IF NOT EXISTS erp_2025 (
  fiscal_year       BIGINT        NOT NULL,
  fiscal_month      BIGINT        NOT NULL,
  trimester         BIGINT        NOT NULL,
  day               BIGINT        NOT NULL,
  month             BIGINT        NOT NULL,
  year              BIGINT        NOT NULL,
  doc_no            BIGINT        NOT NULL,
  doc_date          DATE          NOT NULL,
  funds_ctr         TEXT          NOT NULL,
  cost_ctr_id       TEXT          NOT NULL,
  cost_owner        TEXT,
  cost_note         TEXT,
  io_goods          TEXT,
  io_work           TEXT,
  io_activity       TEXT,
  io_project        TEXT,
  order_description TEXT,
  hr_ot             TEXT,
  gl_id             TEXT          NOT NULL,
  gl_description    TEXT          NOT NULL,
  amount            NUMERIC(18,2) NOT NULL,
  details           TEXT          NOT NULL,
  mu_strategy       NUMERIC,
  ic_strategy       NUMERIC,
  created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ,
  updated_by        TEXT,
  created_by        TEXT
);
