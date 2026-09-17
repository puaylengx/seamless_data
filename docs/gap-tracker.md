# Gap Tracker — seamless_data

> ติ๊กสถานะของ gap G1–G20 จาก [`gap-analysis-2026-09.md`](gap-analysis-2026-09.md) แบ่งตาม phase
> อัปเดตไฟล์นี้**ใน PR เดียวกับโค้ด**ที่ปิด gap (กติกาข้อ 5: audit trail) · เจ้าภาพภาพรวม: Project Manager
> รายละเอียด/ความเสี่ยง/ข้อเสนอของแต่ละ gap ดูใน gap-analysis · เรื่องที่ blocked ดู [`pending-decisions.md`](pending-decisions.md)

**สัญลักษณ์:** `[x]` เสร็จ (merged) · `[~]` กำลังทำ / PR เปิดอยู่ · `[ ]` ยังไม่เริ่ม · 🔒 blocked รอ PD-x · ✋ ทำได้เลย

| Phase | เสร็จ | กำลังทำ | ยังไม่เริ่ม | blocked บางส่วน |
|---|---|---|---|---|
| Phase 0 | 3/3 (zeal half ของ G2 รอ PR #2) | — | — | — |
| Phase 1 | 0/5 | — | 5 | G4 (PD-4), G7 (PD-5) |
| Phase 2 | 0/7 | — | 7 | G5 (PD-3), G10 (Finance), G13 (Finance master file) |
| Phase 3 | 0/6 | — | 6 | G8 (PD-6), G12 (PD-6) |

_อัปเดตล่าสุด: 2026-09-17_

---

## ✅ Phase 0 — production-write safety (เสร็จ 2026-09-17)

- [x] **G9** · Observability · [DevOps] log ของ validator/loader ลงไฟล์ผ่าน `src` logger — [PR #1](https://github.com/puaylengx/seamless_data/pull/1) `5561b47`
- [x] **G3** · Data quality · [QA + Pipeline] track_evaluation fail-fast + `coerce_and_clean()` + validator read-only — [PR #1](https://github.com/puaylengx/seamless_data/pull/1) `d1b4193` · 🔒 ส่วน `reward`=0 รอ PD-2
- [x] **G2** · Security · [Security + Pipeline] `ALLOW_REPLACE` guard ใน `helpers/replace_guard.py` — finance: [PR #1](https://github.com/puaylengx/seamless_data/pull/1) `ca841f7` `bdb8891` `faa53d6`
  - [~] zeal_data half — [PR #2](https://github.com/puaylengx/seamless_data/pull/2) รอ review (base `feat/aditayathorn-zeal-data`)

## Phase 1 — ปิด critical/high ด้าน quality + security (Sprint 1–2)

- [ ] **G1** 🔴 · Testing, CI/CD · [QA + DevOps] ✋ `requirements-dev.txt` + `pyproject.toml` + GitHub Actions (ruff + pytest ทุก PR); test ให้ publication + zeal_data (track_evaluation มีแล้วจาก G3)
- [ ] **G4** 🟠 · Data layering · [Pipeline] ✋ shared prepare สำหรับ MSSQL/BQ + reconciliation step (row count / per-year) · 🔒 ประกาศ source of truth รอ PD-4
- [ ] **G7** 🟠 · Security (Least Privilege) · [Security] ✋ `TRUNCATE` → `DELETE FROM`, เขียน `docs/db-roles.md` (`etl_writer` / `schema_owner`) · 🔒 ตรวจ grant จริงรอ PD-5 (DBA)
- [ ] **G16** 🟡 · Security · [Security] ✋ pre-commit + gitleaks, ย้าย SA JSON ออกนอก repo tree, `sqlalchemy.URL.create()` แทน f-string password
- [ ] **G6** 🟠 · Data modeling · [Architect] ✋ ตาราง `schema_migrations` + `--dry-run` ใน `migrations/migrate.py`; ย้าย BQ DDL / reverse-engineer MSSQL schema เข้า `migrations/research/`

## Phase 2 — architecture / modeling (Sprint 3–4)

- [ ] **G5** 🟠 · Data quality (uniqueness), modeling · [QA + Architect] ✋ migration `003` PK บน `master_*` · 🔒 natural key ของ `erp_2025` รอ PD-3
- [ ] **G10** 🟠 · Data modeling, layering · [Architect] align type `ic_strategy`/`mu_strategy` กับ master, `v_finance_*` view · 🔒 rename `erp_2025` → fact table รอ Finance ยืนยัน structure ข้ามปี
- [ ] **G6** (ต่อ) · [Architect] ✋ DDL research ทั้งหมดอยู่ใน `migrations/` เท่านั้น
- [ ] **G11** 🟡 · Data layering · [Pipeline] ✋ unify pattern `extractor → transformer → validator → loader` ให้ research/zeal; `MasterValidator`
- [ ] **G15** 🟡 · Data modeling · [Architect] ✋ `helpers/fiscal.py` นิยาม fiscal year เดียว + validator cross-check `fiscal_year` vs `doc_date`
- [ ] **G13** 🟡 · Data quality · [QA] ✋ referential check `gl_id`/`cost_ctr_id` กับ master ใน `ErpValidator`; timeliness (as-of) · 🔒 master file ใหม่รอฝ่ายการเงิน
- [ ] **G14** 🟡 · CI/CD · [DevOps] ✋ pin versions, `pyproject.toml` (`pip install -e .`), Dockerfile (mdb-tools + ODBC 18)

## Phase 3 — observability / documentation / dashboard readiness

- [ ] **G12** 🟡 · Documentation · [BI] ✋ `docs/metric-dictionary.md` skeleton · 🔒 นิยาม metric จริง + refresh schedule รอ PD-6 (dashboard tool)
- [ ] **G8** 🟠 · Security (RBAC/PII) · [Security + BI] ✋ data classification table (column → sensitivity) · 🔒 authorized views / policy tags รอ PD-6
- [ ] **G17** 🟡 · Config management · [Pipeline] ✋ ลบ hardcoded infra fallback (`SSH_HOST`, `DB_NAME`), รวม connection เป็น `helpers/connect_db/{postgres,mssql,bigquery}.py`
- [ ] **G18** 🟢 · Documentation · [PM + ทุกคน] ✋ README module map, `docs/decisions/` decision log (ย้ายตาราง "ตัดสินภายในทีมแล้ว" จาก pending-decisions มา), แทน `print()` ที่เหลือ ~30 จุด (ค้างจาก G9)
- [ ] **G19** 🟢 · Data modeling · [Architect] naming `master_io_activities` / `io_good_id` — ทำพร้อม G10 เท่านั้น
- [ ] **G20** 🟢 · Testing · [DevOps] ✋ `@pytest.mark.integration` ให้ `tests/test_connection.py` + skip ใน CI (ทำพร้อม G1 ได้)

---

## งานคู่ขนานที่ไม่ใช่ gap แต่ค้างอยู่

- [~] `feat/finance-fill-cost-owner` `3b923e0` — 🔒 PD-1 (Finance) ยังไม่ push/ไม่ merge
- [~] `fix/odbc-driver-18` `f023f81` — รอ DevOps review (Driver 18 `Encrypt=yes`) ยังไม่ push
- [~] [PR #3](https://github.com/puaylengx/seamless_data/pull/3) docs Phase 0 status + SHA ใหม่ + PD-7 — รอ review
- [~] [PR #4](https://github.com/puaylengx/seamless_data/pull/4) CLAUDE.md + กฎ commit message — รอ review
- [ ] PD-7 ลบ `backup/pre-rewrite/*` tags — หลัง 2026-09-24 รอ owner สั่ง
