-- migration: 003_add_master_primary_keys  (G5 — uniqueness ของ master tables)
--
-- เหตุผล: master_* ไม่มี PK/UNIQUE เลย (002) → append ซ้ำได้เงียบๆ และ erp join กับ master แล้วขยายแถว = double count
-- key ต่อตารางตรงกับ src/finance/master/validator.py::KEY_COLUMNS (MasterValidator กันไฟล์ที่ key ซ้ำก่อนถึง DB)
--
-- ขั้นตอนต่อตาราง (ทั้งไฟล์รันใน transaction เดียวโดย migrations/migrate.py — ล้มตรงไหน rollback หมด):
--   1. ลบ **เฉพาะแถวที่เหมือนกันทุก business column** (exact duplicate) เหลือ 1 แถว — ไม่ตัดสินว่าแถวไหน "ถูก"
--      พบจริงในไฟล์ Master_IO_Goods_20230531.xlsx: io_good_id 76530045 ซ้ำ 2 แถว description เดียวกัน
--      ถ้ามี key ซ้ำแต่ column อื่นต่างกัน → ADD PRIMARY KEY จะ fail → migration rollback → ต้องให้ Finance ตัดสิน (ไม่ลบเดาเอง)
--   2. ADD PRIMARY KEY
-- ตรวจก่อน apply จริง: python migrations/migrate.py finance --dry-run
--
-- ไม่รวม erp_2025: natural key รอ Domain Expert Finance (PD-3)

-- ── master_cost_ctr ───────────────────────────────────────────
DELETE FROM master_cost_ctr a USING master_cost_ctr b
 WHERE a.ctid < b.ctid
   AND a.cost_center_id = b.cost_center_id
   AND a.cost_center_description IS NOT DISTINCT FROM b.cost_center_description
   AND a.cost_center_eng         IS NOT DISTINCT FROM b.cost_center_eng
   AND a.cost_center_th          IS NOT DISTINCT FROM b.cost_center_th
   AND a.status                  IS NOT DISTINCT FROM b.status;
ALTER TABLE master_cost_ctr ADD CONSTRAINT master_cost_ctr_pkey PRIMARY KEY (cost_center_id);

-- ── master_fund ───────────────────────────────────────────────
DELETE FROM master_fund a USING master_fund b
 WHERE a.ctid < b.ctid
   AND a.fund_id = b.fund_id
   AND a.fund_description IS NOT DISTINCT FROM b.fund_description
   AND a.status           IS NOT DISTINCT FROM b.status;
ALTER TABLE master_fund ADD CONSTRAINT master_fund_pkey PRIMARY KEY (fund_id);

-- ── master_gl (gl_id ไม่ซ้ำข้าม group ในไฟล์จริง 187/187 — key คือ gl_id ไม่ใช่ (group_id, gl_id)) ──
DELETE FROM master_gl a USING master_gl b
 WHERE a.ctid < b.ctid
   AND a.gl_id = b.gl_id
   AND a.group_id          IS NOT DISTINCT FROM b.group_id
   AND a.gl_description    IS NOT DISTINCT FROM b.gl_description
   AND a.group_description IS NOT DISTINCT FROM b.group_description
   AND a.status            IS NOT DISTINCT FROM b.status;
ALTER TABLE master_gl ADD CONSTRAINT master_gl_pkey PRIMARY KEY (gl_id);

-- ── master_io_goods ───────────────────────────────────────────
DELETE FROM master_io_goods a USING master_io_goods b
 WHERE a.ctid < b.ctid
   AND a.io_good_id = b.io_good_id
   AND a.io_good_description IS NOT DISTINCT FROM b.io_good_description
   AND a.status              IS NOT DISTINCT FROM b.status;
ALTER TABLE master_io_goods ADD CONSTRAINT master_io_goods_pkey PRIMARY KEY (io_good_id);

-- ── master_io_activities ──────────────────────────────────────
DELETE FROM master_io_activities a USING master_io_activities b
 WHERE a.ctid < b.ctid
   AND a.io_activity_id = b.io_activity_id
   AND a.io_activity_description IS NOT DISTINCT FROM b.io_activity_description
   AND a.status                  IS NOT DISTINCT FROM b.status;
ALTER TABLE master_io_activities ADD CONSTRAINT master_io_activities_pkey PRIMARY KEY (io_activity_id);

-- ── master_io_project ─────────────────────────────────────────
DELETE FROM master_io_project a USING master_io_project b
 WHERE a.ctid < b.ctid
   AND a.io_project_id = b.io_project_id
   AND a.io_project_description IS NOT DISTINCT FROM b.io_project_description
   AND a.cost_center_id         IS NOT DISTINCT FROM b.cost_center_id
   AND a.ic_strategy_id         IS NOT DISTINCT FROM b.ic_strategy_id
   AND a.mu_strategy_id         IS NOT DISTINCT FROM b.mu_strategy_id
   AND a.status                 IS NOT DISTINCT FROM b.status;
ALTER TABLE master_io_project ADD CONSTRAINT master_io_project_pkey PRIMARY KEY (io_project_id);

-- ── master_io_work ────────────────────────────────────────────
DELETE FROM master_io_work a USING master_io_work b
 WHERE a.ctid < b.ctid
   AND a.io_work_id = b.io_work_id
   AND a.io_work_description IS NOT DISTINCT FROM b.io_work_description
   AND a.status              IS NOT DISTINCT FROM b.status;
ALTER TABLE master_io_work ADD CONSTRAINT master_io_work_pkey PRIMARY KEY (io_work_id);

-- ── master_ic_strategy ────────────────────────────────────────
DELETE FROM master_ic_strategy a USING master_ic_strategy b
 WHERE a.ctid < b.ctid
   AND a.ic_strategy_id = b.ic_strategy_id
   AND a.start_year              IS NOT DISTINCT FROM b.start_year
   AND a.end_year                IS NOT DISTINCT FROM b.end_year
   AND a.name_en                 IS NOT DISTINCT FROM b.name_en
   AND a.ic_strategy_description IS NOT DISTINCT FROM b.ic_strategy_description
   AND a.status                  IS NOT DISTINCT FROM b.status;
ALTER TABLE master_ic_strategy ADD CONSTRAINT master_ic_strategy_pkey PRIMARY KEY (ic_strategy_id);

-- ── master_mu_strategy ────────────────────────────────────────
DELETE FROM master_mu_strategy a USING master_mu_strategy b
 WHERE a.ctid < b.ctid
   AND a.mu_strategy_id = b.mu_strategy_id
   AND a.start_year              IS NOT DISTINCT FROM b.start_year
   AND a.end_year                IS NOT DISTINCT FROM b.end_year
   AND a.name_en                 IS NOT DISTINCT FROM b.name_en
   AND a.mu_strategy_description IS NOT DISTINCT FROM b.mu_strategy_description
   AND a.status                  IS NOT DISTINCT FROM b.status;
ALTER TABLE master_mu_strategy ADD CONSTRAINT master_mu_strategy_pkey PRIMARY KEY (mu_strategy_id);
