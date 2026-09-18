-- migration: 003_add_master_primary_keys  (G5 — uniqueness ของ master tables)
--
-- เหตุผล: master_* ไม่มี PK/UNIQUE เลย (002) → append ซ้ำได้เงียบๆ และ erp join กับ master แล้วขยายแถว = double count
-- key ต่อตารางตรงกับ src/finance/master/validator.py::KEY_COLUMNS (MasterValidator กันไฟล์ที่ key ซ้ำก่อนถึง DB)
--
-- ไฟล์นี้ **เพิ่ม constraint เท่านั้น ไม่ลบข้อมูลใดๆ** — ถ้าตารางไหนมี key ซ้ำอยู่แล้ว ADD PRIMARY KEY จะ fail
-- และ migrations/migrate.py rollback ทั้ง transaction → นี่คือ "ตรวจจับ" โดยตั้งใจ ไม่ใช่ "แก้ไข"
-- (พบจริง: io_good_id 76530045 ซ้ำใน Master_IO_Goods_20230531.xlsx → ลบได้เฉพาะเมื่อ Finance ยืนยัน → 004 + PD-11)
-- ตรวจก่อน apply จริง: python migrations/migrate.py finance --dry-run
--
-- ไม่รวม erp_2025: natural key รอ Domain Expert Finance (PD-3)

ALTER TABLE master_cost_ctr      ADD CONSTRAINT master_cost_ctr_pkey      PRIMARY KEY (cost_center_id);
ALTER TABLE master_fund          ADD CONSTRAINT master_fund_pkey          PRIMARY KEY (fund_id);
-- gl_id ไม่ซ้ำข้าม group ในไฟล์จริง 187/187 → key คือ gl_id ไม่ใช่ (group_id, gl_id)
ALTER TABLE master_gl            ADD CONSTRAINT master_gl_pkey            PRIMARY KEY (gl_id);
ALTER TABLE master_io_goods      ADD CONSTRAINT master_io_goods_pkey      PRIMARY KEY (io_good_id);
ALTER TABLE master_io_activities ADD CONSTRAINT master_io_activities_pkey PRIMARY KEY (io_activity_id);
ALTER TABLE master_io_project    ADD CONSTRAINT master_io_project_pkey    PRIMARY KEY (io_project_id);
ALTER TABLE master_io_work       ADD CONSTRAINT master_io_work_pkey       PRIMARY KEY (io_work_id);
ALTER TABLE master_ic_strategy   ADD CONSTRAINT master_ic_strategy_pkey   PRIMARY KEY (ic_strategy_id);
ALTER TABLE master_mu_strategy   ADD CONSTRAINT master_mu_strategy_pkey   PRIMARY KEY (mu_strategy_id);
