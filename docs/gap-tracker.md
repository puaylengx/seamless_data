# Gap Tracker — seamless_data

> ติ๊กสถานะของ gap G1–G20 จาก [`gap-analysis-2026-09.md`](gap-analysis-2026-09.md) แบ่งตาม phase
> อัปเดตไฟล์นี้**ใน PR เดียวกับโค้ด**ที่ปิด gap (กติกาข้อ 5: audit trail) · เจ้าภาพภาพรวม: Project Manager
> รายละเอียด/ความเสี่ยง/ข้อเสนอของแต่ละ gap ดูใน gap-analysis · เรื่องที่ blocked ดู [`pending-decisions.md`](pending-decisions.md)

**สัญลักษณ์:** `[x]` เสร็จ (merged) · `[~]` กำลังทำ / PR เปิดอยู่ · `[ ]` ยังไม่เริ่ม · 🔒 blocked รอ PD-x · ✋ ทำได้เลย

| Phase | เสร็จ | กำลังทำ | ยังไม่เริ่ม | blocked บางส่วน |
|---|---|---|---|---|
| Phase 0 | 3/3 (zeal half ของ G2 รอ PR #2) | — | — | — |
| Phase 1 | 4/5 + G6 ส่วนที่ทำได้ ✅ #13 (G1 ✅ #6 · G4 ✅ #9 · G7 ✅ #10 · G16 ✅ #11) | — | 0 | G4 SoT (PD-4), G7 grants (PD-5), G6 MSSQL (PD-9) |
| Phase 2 | 6/8 (G14 ✅ #14 · G15 ✅ #15 · G11 ✅ #16 · G5 PK ✅ #17 · G13 ✅ #18 · G21 ✅ #20) | — | 2 (G10 🔒, G6 MSSQL 🔒) | G5 erp key (PD-3) + io_goods dedupe (PD-11b), G10 (Finance), G13 master ใหม่ (PD-13) + funds_ctr (PD-12), G21 (PD-8), G15 policy (PD-10) |
| Phase 3 | 3/7 (G20 ✅ #6 · G17 ✅ #21 · G18 ✅ #22) | G9 follow-up (PR #23) | 4 | G8 (PD-6), G12 (PD-6) |

_อัปเดตล่าสุด: 2026-09-18 (G17/G18 merged; G9 follow-up → #23)_

---

## ✅ Phase 0 — production-write safety (เสร็จ 2026-09-17)

- [x] **G9** · Observability · [DevOps] log ของ validator/loader ลงไฟล์ผ่าน `src` logger — [PR #1](https://github.com/puaylengx/seamless_data/pull/1) `5561b47` · **follow-up (PR #23):** เฉพาะ entrypoint `__main__` เป็นเจ้าของ `src` handlers — module ที่ถูก import ตั้ง logger ตัวเองได้แต่ไม่แย่ง `src` (กันเคสแบบ #22 ทั่วไป)
- [x] **G3** · Data quality · [QA + Pipeline] track_evaluation fail-fast + `coerce_and_clean()` + validator read-only — [PR #1](https://github.com/puaylengx/seamless_data/pull/1) `d1b4193` · 🔒 ส่วน `reward`=0 รอ PD-2
- [x] **G2** · Security · [Security + Pipeline] `ALLOW_REPLACE` guard ใน `helpers/replace_guard.py` — finance: [PR #1](https://github.com/puaylengx/seamless_data/pull/1) `ca841f7` `bdb8891` `faa53d6`
  - [~] zeal_data half — [PR #2](https://github.com/puaylengx/seamless_data/pull/2) รอ review (base `feat/aditayathorn-zeal-data`)

## Phase 1 — ปิด critical/high ด้าน quality + security (Sprint 1–2)

- [x] **G1** 🔴 · Testing, CI/CD · [QA + DevOps] [PR #6](https://github.com/puaylengx/seamless_data/pull/6) merged `99f8759` — `pyproject.toml` + `requirements-dev.txt` + GitHub Actions (ruff + pytest ทุก PR) `59085e6`; publication tests 36 cases (74 → 110 passed). zeal_data tests อยู่บน branch ตระกูล zeal (loader: PR #2, extractor: ตามมา)
- [x] **G4** 🟠 · Data layering · [Pipeline + QA] [PR #9](https://github.com/puaylengx/seamless_data/pull/9) merged — `prepare_for_load()` ตัวเดียวสำหรับ MSSQL/BQ (track_evaluation), `src/research/reconcile.py` (rows/distinct key ต่อปี, prepared vs ปลายทาง, MSSQL ⇄ BQ) เรียกหลังทุก upload ทั้งสอง pipeline; +22 tests (110 → 132) · 🔒 ประกาศ source of truth รอ PD-4 — reconcile จึงแค่ WARNING ไม่ raise
- [x] **G7** 🟠 · Security (Least Privilege) · [Security] [PR #10](https://github.com/puaylengx/seamless_data/pull/10) merged `fe9c7a0` — finance ERP/master `replace` ใช้ `DELETE FROM` แทน `TRUNCATE` (DML อย่างเดียว, transaction เดียวกับ INSERT); [`docs/db-roles.md`](db-roles.md) role matrix `schema_owner` / `etl_writer` / `bi_reader` + query ตรวจสิทธิ์ PG/MSSQL/BQ + checklist; test ยืนยันไม่มี DDL ใน SQL ที่ loader ส่ง · 🔒 ตรวจ/ลด grant จริงรอ PD-5 (DBA) · ข้อยกเว้นที่รู้: zeal `replace` ยัง DROP+CREATE (ต้องรอ G6/G11)
- [x] **G16** 🟡 · Security · [Security] [PR #11](https://github.com/puaylengx/seamless_data/pull/11) merged `5cc92a4` — gitleaks สแกน history ทั้ง repo (76 commits) = 0 leaks; `.pre-commit-config.yaml` (gitleaks, detect-private-key, ruff, large files) + gitleaks step ใน CI (fetch-depth 0); SA JSON ย้ายไป `~/.config/seamless_data/` (copy → sha256 → auth dry-run → ลบต้นฉบับ) + `.gitignore` เพิ่ม `configs/secrets/ .env.* *.pem *.key`; `helpers/connect_db/urls.py` `URL.create()` แทน f-string ทั้ง MSSQL/PG-ssh/PG-direct (10 tests) · zeal PG URL f-string ยังอยู่บน branch zeal → ใช้ `postgres_url()` ตอน merge
- [~] **G6** 🟠 · Data modeling · [Architect + DevOps] [PR #13](https://github.com/puaylengx/seamless_data/pull/13) merged `0b3570a` — ✅ `schema_migrations` + `--dry-run`/`--status` + checksum guard ใน `migrate.py` (`078864f`, 11 tests) · ✅ BQ DDL/view ย้ายไป `migrations/research/bigquery/` + `migrations/README.md` (`7c2e0c8`) · 🔒 **MSSQL `001_*.sql` reverse-engineer รอ PD-9** (instance ที่ `.env` ชี้ไม่ได้รัน — query read-only เตรียมไว้แล้ว)

## Phase 2 — architecture / modeling (Sprint 3–4)

- [x] **G5** 🟠 · Data quality (uniqueness), modeling · [QA + Architect] [PR #17](https://github.com/puaylengx/seamless_data/pull/17) merged `547db92` — **PK master ✅** `003_add_master_primary_keys.sql` (ADD PRIMARY KEY อย่างเดียว key = `MasterValidator.KEY_COLUMNS`; ไม่ลบข้อมูล; พิสูจน์บน PG16 ชั่วคราวว่า DB ที่มี `76530045` ซ้ำ → `UniqueViolation` → rollback ทั้ง transaction, หลัง dedupe → PK 9 ตาราง + `schema_migrations` ครบ) · **dedupe io_goods 🔒 PD-11b** `004_dedupe_io_goods.sql` (`-- migrate: manual` → migrate.py ข้ามเสมอ, apply ได้เฉพาะ `--only`) · apply จริงต้อง `--dry-run` บน staging ก่อน (DevOps) · 🔒 natural key `erp_2025` รอ PD-3
- [ ] **G10** 🟠 · Data modeling, layering · [Architect] align type `ic_strategy`/`mu_strategy` กับ master, `v_finance_*` view · 🔒 rename `erp_2025` → fact table รอ Finance ยืนยัน structure ข้ามปี
- [ ] **G6** (ต่อ) · [Architect] BQ `track_evaluation` DDL ยังไม่มีใน repo (ไม่เคยมี) — ดึง schema จาก `client.get_table()` (metadata) ต้องขออนุญาตแยกเหมือน MSSQL · MSSQL 🔒 PD-9
- [x] **G11** 🟡 · Data layering · [Pipeline + QA] [PR #16](https://github.com/puaylengx/seamless_data/pull/16) merged `74a174c` — publication: `extractor.py` (read_raw ตรวจ column บังคับ / read_reviewed_template), template assembly ย้ายจาก main → `transformer.build_publication_template`, **validator read-only** (month-fill ย้ายไป `coerce_and_clean` ตาม pattern G3; test G1 ที่ assert mutation เขียนใหม่ให้ตรวจผ่าน transformer) · track_evaluation: `extractor.py` · finance master: `MasterValidator` (key ว่าง/ซ้ำ/column หาย → fail, status แปลก → warning) เข้า main ก่อน load · **zeal_data ยังไม่แตะ** (module อยู่ branch zeal — ทำหลัง #2/#7 merge)
- [x] **G15** 🟡 · Data modeling · [Architect + QA] [PR #15](https://github.com/puaylengx/seamless_data/pull/15) merged `dd9d491` · 🔒 ตัดสิน fail/ยึด doc_date/ยึด Excel รอ PD-10 — `helpers/fiscal.py` (`FISCAL_YEAR_START_MONTH=10`, `fiscal_month` / `fiscal_year` / `fiscal_year_from_date`) ใช้ทั้ง finance `add_fiscal_month` และ research `get_clean_budget_year` — test พิสูจน์ผลเท่าสูตรเดิมทุกกรณีรวม NaN; `ErpValidator.validate_fiscal_year_vs_doc_date` cross-check `fiscal_year`/`fiscal_month` จาก Excel vs derive จาก `doc_date` → **WARNING + `result["warnings"]` ไม่ block** (เก็บสถิติก่อนตัดสิน fail-fast)
- [x] **G13** 🟡 · Data quality · [QA] [PR #18](https://github.com/puaylengx/seamless_data/pull/18) merged `569c3ff` — `src/finance/reference.py` (reference sets จากไฟล์ master ผ่าน extractor/transformer เดิม, `normalize_key` ให้ NUMERIC 3.0 เทียบ TEXT '3' ได้, `master_as_of` จากชื่อไฟล์) · `ErpValidator.validate_referential` (WARNING default / `strict_reference=True` → error) + `validate_timeliness` (doc_date ล่าสุด > 120 วัน, master > 365 วัน → WARNING) ต่อเข้า finance main · รันกับไฟล์จริง: cost_ctr ตรงครบ, gl/io_goods/io_project/io_work มีรหัสใหม่ → 🔒 **PD-13** ขอ master ใหม่; `funds_ctr` คนละระบบรหัสกับ master_fund → ถอดออก 🔒 **PD-12**
- [x] **G21** 🟡 · Data quality · [QA + Domain Expert Research] [PR #20](https://github.com/puaylengx/seamless_data/pull/20) merged `d63e797` — ✋ range check ปี 2000–2100 ใน `validate_publication` (จับ `"2023 (RC3)"` → 20233 ได้แล้ว, log บอกค่าที่พบ) · 🔒 แก้ `get_clean_year` (reject/strip suffix) + validate `rank` กับ `_VALID_RANKS` รอ PD-8
- [x] **G14** 🟡 · CI/CD · [DevOps] [PR #14](https://github.com/puaylengx/seamless_data/pull/14) merged `c7cce4d` — `requirements*.txt` pin `==` ทุกตัว (pandas 3.0.3, numpy 2.4.6, SQLAlchemy 2.0.50 …) ยืนยันใน fresh venv: 148 passed + `pip check` สะอาด; `Dockerfile` multi-stage (`runtime` ไม่มี dev deps/tests · `test` = runtime + dev + tests) python:3.12-slim + mdbtools + unixODBC + msodbcsql18, non-root, build-time assert ว่า ODBC 18 มีจริงและ pytest **ไม่** อยู่ใน runtime; `.dockerignore` กัน credential/data; CI job `docker-build` (build เท่านั้น) · `pyproject.toml` มีแล้วจาก G1

## Phase 3 — observability / documentation / dashboard readiness

- [ ] **G12** 🟡 · Documentation · [BI] ✋ `docs/metric-dictionary.md` skeleton · 🔒 นิยาม metric จริง + refresh schedule รอ PD-6 (dashboard tool)
- [ ] **G8** 🟠 · Security (RBAC/PII) · [Security + BI] ✋ data classification table (column → sensitivity) · 🔒 authorized views / policy tags รอ PD-6
- [x] **G17** 🟡 · Config management · [Pipeline + DevOps] [PR #21](https://github.com/puaylengx/seamless_data/pull/21) merged `b023350` — `helpers/connect_db/config.py` ตรวจ env ครบก่อนแตะ network, `MissingConfigError` บอกชื่อ var ที่ขาด**ทั้งหมด** + วิธีแก้ (ไม่มี fallback `192.168.64.2`/`ic_finance`/`localhost` แล้ว; เหลือ protocol default 22/5432/public) · `mssql.py` / `bigquery.py` factories ใช้ร่วม publication + track_evaluation (ลบ `_mssql_engine`/`_bq_tables` ที่ซ้ำ), `MSSQL_ODBC_DRIVER` ตั้งผ่าน env · `connection.py` print → logger · zeal PG tunnel ยังซ้ำอยู่บน branch zeal
- [x] **G18** 🟢 · Documentation · [PM + ทุกคน] [PR #22](https://github.com/puaylengx/seamless_data/pull/22) merged `002ac38` — README quick start + module map · `docs/decisions/` 10 ไฟล์ (ย้ายตาราง "ตัดสินภายในทีมแล้ว" + เพิ่มการตัดสินใจจาก G4/G5/G13/G15) · `print()` → logger ครบ (finance ERP/master, research usage) + บรรทัด `JOB SUMMARY` ท้ายทุก run (ค้างจาก G9) · แก้ side effect ที่พบระหว่างทาง: `MASTER_FILES` ย้ายไป `master/files.py` เพราะ import `master.main` แย่ง handler ของ `src` logger
- [ ] **G19** 🟢 · Data modeling · [Architect] naming `master_io_activities` / `io_good_id` — ทำพร้อม G10 เท่านั้น
- [ ] **G22** 🟢 · Security / CI · [DevOps] ✋ CI gitleaks (gitleaks-action บน pull_request) สแกนเฉพาะ commit ของ PR ไม่ใช่ full history — เพิ่ม scheduled workflow (เช่น weekly) รัน `gitleaks git --log-opts=--all` แยกจาก PR check (full-history scan ล่าสุดทำในเครื่อง 2026-09-17 = 0 leaks, PR #11)
- [x] **G20** 🟢 · Testing · [DevOps] ทำพร้อม G1 ใน [PR #6](https://github.com/puaylengx/seamless_data/pull/6) — `pytestmark = integration`, deselect ผ่าน pyproject `addopts`

---

## งานคู่ขนานที่ไม่ใช่ gap แต่ค้างอยู่

- [~] `feat/finance-fill-cost-owner` `3b923e0` — 🔒 PD-1 (Finance) ยังไม่ push/ไม่ merge
- [~] `fix/odbc-driver-18` `f023f81` — รอ DevOps review (Driver 18 `Encrypt=yes`) ยังไม่ push
- [x] [PR #3](https://github.com/puaylengx/seamless_data/pull/3) docs Phase 0 status + SHA ใหม่ + PD-7 — merged `36c5c93`
- [x] [PR #4](https://github.com/puaylengx/seamless_data/pull/4) CLAUDE.md + กฎ commit message — merged `8590a64`
- [x] [PR #5](https://github.com/puaylengx/seamless_data/pull/5) gap tracker (ไฟล์นี้) — merged `3cbe7cc`
- [ ] PD-7 ลบ `backup/pre-rewrite/*` tags — หลัง 2026-09-24 รอ owner สั่ง
