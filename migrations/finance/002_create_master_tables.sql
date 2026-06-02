-- migration: 002_create_master_tables

CREATE TABLE IF NOT EXISTS master_cost_ctr (
  cost_center_id          TEXT NOT NULL,
  cost_center_description TEXT,
  cost_center_eng         TEXT,
  cost_center_th          TEXT,
  status                  TEXT,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ,
  updated_by              TEXT,
  created_by              TEXT
);

CREATE TABLE IF NOT EXISTS master_fund (
  fund_id          TEXT NOT NULL,
  fund_description TEXT,
  status           TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ,
  updated_by       TEXT,
  created_by       TEXT
);

CREATE TABLE IF NOT EXISTS master_gl (
  group_id          TEXT NOT NULL,
  gl_id             TEXT NOT NULL,
  gl_description    TEXT,
  group_description TEXT,
  status            TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ,
  updated_by        TEXT,
  created_by        TEXT
);

CREATE TABLE IF NOT EXISTS master_io_goods (
  io_good_id          TEXT NOT NULL,
  io_good_description TEXT,
  status              TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ,
  updated_by          TEXT,
  created_by          TEXT
);

CREATE TABLE IF NOT EXISTS master_io_activities (
  io_activity_id          TEXT NOT NULL,
  io_activity_description TEXT,
  status                  TEXT,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ,
  updated_by              TEXT,
  created_by              TEXT
);

CREATE TABLE IF NOT EXISTS master_io_project (
  io_project_id          TEXT NOT NULL,
  io_project_description TEXT,
  cost_center_id         TEXT,
  ic_strategy_id         TEXT,
  mu_strategy_id         TEXT,
  status                 TEXT,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at             TIMESTAMPTZ,
  updated_by             TEXT,
  created_by             TEXT
);

CREATE TABLE IF NOT EXISTS master_io_work (
  io_work_id          TEXT NOT NULL,
  io_work_description TEXT,
  status              TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ,
  updated_by          TEXT,
  created_by          TEXT
);

CREATE TABLE IF NOT EXISTS master_ic_strategy (
  ic_strategy_id          TEXT NOT NULL,
  start_year              BIGINT,
  end_year                BIGINT,
  name_en                 TEXT,
  ic_strategy_description TEXT,
  status                  TEXT,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ,
  updated_by              TEXT,
  created_by              TEXT
);

CREATE TABLE IF NOT EXISTS master_mu_strategy (
  mu_strategy_id          TEXT NOT NULL,
  start_year              BIGINT,
  end_year                BIGINT,
  name_en                 TEXT,
  mu_strategy_description TEXT,
  status                  TEXT,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ,
  updated_by              TEXT,
  created_by              TEXT
);
