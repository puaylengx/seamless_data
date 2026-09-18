# Gap Tracker — seamless_data

> ติ๊กสถานะของ gap G1–G20 จาก [`gap-analysis-2026-09.md`](gap-analysis-2026-09.md) แบ่งตาม phase
> อัปเดตไฟล์นี้**ใน PR เดียวกับโค้ด**ที่ปิด gap (กติกาข้อ 5: audit trail) · เจ้าภาพภาพรวม: Project Manager
> รายละเอียด/ความเสี่ยง/ข้อเสนอของแต่ละ gap ดูใน gap-analysis · เรื่องที่ blocked ดู [`pending-decisions.md`](pending-decisions.md)

**สัญลักษณ์:** `[x]` เสร็จ (merged) · `[~]` กำลังทำ / PR เปิดอยู่ · `[ ]` ยังไม่เริ่ม · 🔒 blocked รอ PD-x · ✋ ทำได้เลย

| Phase | เสร็จ | กำลังทำ | ยังไม่เริ่ม | blocked บางส่วน |
|---|---|---|---|---|
| Phase 0 | 3/3 (zeal half ของ G2 รอ PR #2) | — | — | — |
| Phase 1 | 4/5 + G6 ส่วนที่ทำได้ ✅ #13 (G1 ✅ #6 · G4 ✅ #9 · G7 ✅ #10 · G16 ✅ #11) | — | 0 | G4 SoT (PD-4), G7 grants (PD-5), G6 MSSQL (PD-9) |
| Phase 2 | 0/8 | G14 (PR #14) | 7 | G5 (PD-3), G10 (Finance), G13 (Finance master file), G21 (PD-8) |
| Phase 3 | 1/7 (G20 ✅ PR #6) | — | 6 | G8 (PD-6), G12 (PD-6) |

_อัปเดตล่าสุด: 2026-09-18 (G6 → PR #13; PD-9)_

---

## ✅ Phase 0 — production-write safety (เสร็จ 2026-09-17)

- [x] **G9** · Observability · [DevOps] log ของ validator/loader ลงไฟล์ผ่าน `src` logger — [PR #1](https://github.com/puaylengx/seamless_data/pull/1) `5561b47`
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

- [ ] **G5** 🟠 · Data quality (uniqueness), modeling · [QA + Architect] ✋ migration `003` PK บน `master_*` · 🔒 natural key ของ `erp_2025` รอ PD-3
- [ ] **G10** 🟠 · Data modeling, layering · [Architect] align type `ic_strategy`/`mu_strategy` กับ master, `v_finance_*` view · 🔒 rename `erp_2025` → fact table รอ Finance ยืนยัน structure ข้ามปี
- [ ] **G6** (ต่อ) · [Architect] BQ `track_evaluation` DDL ยังไม่มีใน repo (ไม่เคยมี) — ดึง schema จาก `client.get_table()` (metadata) ต้องขออนุญาตแยกเหมือน MSSQL · MSSQL 🔒 PD-9
- [ ] **G11** 🟡 · Data layering · [Pipeline] ✋ unify pattern `extractor → transformer → validator → loader` ให้ research/zeal; `MasterValidator` · **note:** publication `validate_publication` ยัง mutate df (เติม `publication_month` จาก `effective_date`) — เคสเดียวกับที่แก้ใน track_evaluation (G3) ต้องย้ายไป transformer พร้อมกัน (พบใน [PR #6](https://github.com/puaylengx/seamless_data/pull/6))
- [ ] **G15** 🟡 · Data modeling · [Architect] ✋ `helpers/fiscal.py` นิยาม fiscal year เดียว + validator cross-check `fiscal_year` vs `doc_date`
- [ ] **G13** 🟡 · Data quality · [QA] ✋ referential check `gl_id`/`cost_ctr_id` กับ master ใน `ErpValidator`; timeliness (as-of) · 🔒 master file ใหม่รอฝ่ายการเงิน
- [ ] **G21** 🟡 · Data quality · [QA + Domain Expert Research] Publication validator ไม่ตรวจ Year suffix (`"2023 (RC3)"` → `20233` เงียบๆ ผ่าน `get_clean_year`) และไม่ validate `rank` กับ `_VALID_RANKS` (`"Dr."` หลุดผ่าน) — พบระหว่างเขียน test ของ G1 ([PR #6](https://github.com/puaylengx/seamless_data/pull/6)) · 🔒 เกณฑ์ที่ถูกต้องรอ PD-8 · ✋ เพิ่ม range check ปี (เช่น 2000–2100) ทำได้เลย
- [~] **G14** 🟡 · CI/CD · [DevOps] PR #14 รอ review — `requirements*.txt` pin `==` ทุกตัว (pandas 3.0.3, numpy 2.4.6, SQLAlchemy 2.0.50 …) ยืนยันใน fresh venv: 148 passed + `pip check` สะอาด; `Dockerfile` multi-stage (`runtime` ไม่มี dev deps/tests · `test` = runtime + dev + tests) python:3.12-slim + mdbtools + unixODBC + msodbcsql18, non-root, build-time assert ว่า ODBC 18 มีจริงและ pytest **ไม่** อยู่ใน runtime; `.dockerignore` กัน credential/data; CI job `docker-build` (build เท่านั้น) · `pyproject.toml` มีแล้วจาก G1

## Phase 3 — observability / documentation / dashboard readiness

- [ ] **G12** 🟡 · Documentation · [BI] ✋ `docs/metric-dictionary.md` skeleton · 🔒 นิยาม metric จริง + refresh schedule รอ PD-6 (dashboard tool)
- [ ] **G8** 🟠 · Security (RBAC/PII) · [Security + BI] ✋ data classification table (column → sensitivity) · 🔒 authorized views / policy tags รอ PD-6
- [ ] **G17** 🟡 · Config management · [Pipeline] ✋ ลบ hardcoded infra fallback (`SSH_HOST`, `DB_NAME`), รวม connection เป็น `helpers/connect_db/{postgres,mssql,bigquery}.py`
- [ ] **G18** 🟢 · Documentation · [PM + ทุกคน] ✋ README module map, `docs/decisions/` decision log (ย้ายตาราง "ตัดสินภายในทีมแล้ว" จาก pending-decisions มา), แทน `print()` ที่เหลือ ~30 จุด (ค้างจาก G9)
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
