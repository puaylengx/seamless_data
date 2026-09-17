# seamless_data — Gap Analysis vs. International Standards (2026-09)

> อ้างอิงหัวข้อ "มาตรฐานสากลที่ยึดถือ" ใน [`docs/team-project-instructions.md`](team-project-instructions.md)
> ตรวจสอบจากโค้ดจริงทั้ง repo (helpers, migrations, src ทั้ง 4 module, tests, docs,
> .env/.env.example, git history/branches, logs จริง) เรียงตามความสำคัญ ไม่เรียงตามหมวด
>
> **สถานะ Phase 0 (2026-09-17):** กำลัง implement บน branch
> `fix/phase0-production-write-safety` (แยกจาก main `3280f36`) — ดู G2, G3, G9 ด้านล่าง
> รายการ blocked ที่รอคำตอบจากนอกทีมดูที่ [`docs/pending-decisions.md`](pending-decisions.md)

---

## สรุปภาพรวม (Project Manager)

| หมวดมาตรฐาน | สถานะรวม | เจ้าภาพ |
|---|---|---|
| Config management (12-Factor) | ตรง เป็นส่วนใหญ่ — .env ครบ, gitignore ครอบคลุม, ไม่มี secret ใน git history | DevOps / Security |
| Version control (Conventional Commits) | ตรง — commit ทุกตัวใช้ feat/fix/docs/chore(scope) และ feature-branch flow | ทุกคน |
| Testing (test pyramid) | ใกล้เคียง เฉพาะ finance / ไม่ตรงเลย สำหรับ research + zeal_data (track_evaluation จะได้ test ชุดแรกจาก G3 ใน Phase 0) | QA |
| CI/CD | ไม่ตรงเลย — ไม่มี workflow, ไม่มี lint, pytest ไม่อยู่ใน requirements | DevOps + QA |
| Security (Least Privilege / opt-in flag) | ใกล้เคียง research / ไม่ตรง finance, zeal_data → G2 กำลังแก้ใน Phase 0 | Security |
| Data quality (DAMA) | ใกล้เคียง — completeness/accuracy มี, uniqueness/consistency/timeliness ไม่มี | QA |
| Data layering (Medallion) | ใกล้เคียง — มีบน disk (01_raw/02_template/03_export) แต่ใน DB มี layer เดียว | Architect |
| Data modeling (Kimball) | ใกล้เคียง — มี master_* เป็น dimension แต่ไม่มี PK/FK, fact ตั้งชื่อตามปี | Architect |
| Observability | ไม่ตรง — log ของ validator/loader หายจริง → G9 กำลังแก้ใน Phase 0 | DevOps |
| Documentation (Metric Dictionary) | ไม่ตรงเลย — ไม่มี Metric Dictionary, README 1 บรรทัด, ไม่มี decision log | BI + PM |

---

## 🔴 CRITICAL

### G1 · [Data Quality Engineer + DevOps] ไม่มี CI gate และ research/zeal_data ไม่มี test เลย — Testing, CI/CD

**สถานะ:** ไม่ตรงเลย — มี test เฉพาะ `tests/finance/` (3 ไฟล์ ✓) แต่ `src/research/*` และ `src/aditayathorn/*` ไม่มี test แม้แต่ไฟล์เดียว (ก่อน Phase 0) ทั้งที่เขียนเข้า `muic-data-prod` BigQuery และ MSSQL จริง; ไม่มี `.github/workflows`, ไม่มี lint config, pytest ไม่อยู่ใน `requirements.txt` (รัน `python -m pytest` ใน `.venv` แล้วขึ้น "No module named pytest")

**ความเสี่ยง:** กติกา "merge ไม่ได้ถ้า pipeline ที่เขียน production ไม่มี test" บังคับใช้ไม่ได้เลยตอนนี้ — ตัวเลข publication ranking / track evaluation ที่ผิด (ซึ่งผูกกับ reward นักวิจัยและ KPI ระดับคณะ) จะขึ้น dashboard โดยไม่มีใครตรวจ

**ข้อเสนอ:**
1. เพิ่ม `requirements-dev.txt` (pytest, ruff), `pyproject.toml` → ทำได้เลย
2. GitHub Actions: ruff + pytest ทุก PR → ทำได้เลย
3. เขียน `test_transformer.py` + `test_validator.py` ให้ publication และ track_evaluation (track_evaluation ทำแล้วบางส่วนใน Phase 0) — transformer เป็น pure function ทดสอบง่าย (SDG parse, `_parse_database_entry`, budget_year, rank normalize) → ทำได้เลย

---

### G2 · [Security Engineer + Pipeline Engineer] Production write ไม่ opt-in สำหรับ finance และ zeal_data; research มี flag แต่เปิดค้างไว้ — Security

**สถานะ:** 🔄 **กำลังทำใน Phase 0** (planned commit `fix(safety): require ALLOW_REPLACE=true before destructive replace mode`) — เพิ่ม `ALLOW_REPLACE` env guard ก่อนรัน replace ทั้ง finance/zeal_data, เปลี่ยน `ZEAL_INSERT_MODE` default เป็น `append`

**ทำแล้ว (2026-09-17):** ตรวจ `.env` จริงบนเครื่อง — `PUBLICATION_UPLOAD_BQ` และ `TRACK_EVAL_UPLOAD_BQ` เป็น `false` แล้ว (คนละเรื่องกับ guard ที่เพิ่ม เพราะ flag พวกนี้ควบคุมคนละปลายทาง) → **ยังต้องทำ:** เพิ่มใน pre-deployment checklist ว่า "reset flag เป็น false หลัง upload เสร็จ"

---

### G3 · [Data Quality Engineer] track_evaluation เขียน DB ต่อแม้ validation fail + validator แก้ข้อมูลเอง — Data quality, กติกาข้อ 3

**สถานะ:** 🔄 **กำลังทำใน Phase 0** (planned commit `fix(track_evaluation): fail-fast on validation error, move coercion out of validator`) — fail-fast แบบเดียวกับ publication (`sys.exit(1)`); ย้าย coercion/fill ทั้งหมดไป `transformer.coerce_and_clean()`; เพิ่ม test_transformer/test_validator

**ยัง blocked:** reward ที่ parse ไม่ได้ยัง fillna(0) ตาม behavior เดิม (จะใส่ `TODO` ไว้ในโค้ด) — **ต้องให้ Domain Expert Research ยืนยันว่า reward ว่าง = 0 จริง หรือควร reject**

---

## 🟠 HIGH

### G4 · [Pipeline Engineer] สองปลายทาง (MSSQL vs BigQuery) semantics ต่างกัน ไม่มี source of truth ไม่มี reconciliation — Data layering, หน้าที่พิเศษข้อ 2

**สถานะ:** ไม่ตรงเลย — MSSQL ใช้ `to_sql(if_exists="append")` (ซ้ำได้) แต่ BQ ใช้ staging + MERGE (upsert, idempotent); *(อัปเดต: การที่ `run_upload_bq` ไม่เติม month/year/order_num เหมือน `run_upload` ถูกแก้ไปแล้วเป็นผลพลอยได้จาก G3 เพราะตอนนี้ทั้งคู่เรียก `coerce_and_clean()` ตัวเดียวกัน)*

**ความเสี่ยง:** ตัวเลขที่ฝ่ายวิจัย query จาก MSSQL กับที่ dashboard อ่านจาก BQ ไม่ตรงกันโดยออกแบบ

**ข้อเสนอ:** เพิ่ม reconciliation step หลัง upload (row count + count per publication_year เทียบสอง DB, log ผลลัพธ์) → ทำได้เลย; ประกาศว่าอันไหนเป็น source of truth → **blocked รอ business owner ตัดสิน**

---

### G5 · [Data Quality Engineer + Data Architect] ไม่มี PK/UNIQUE ในตารางใดเลย → รันซ้ำแล้วซ้ำแถว — Data quality (uniqueness), Data modeling

**สถานะ:** ไม่ตรงเลย — `migrations/finance/` ทั้ง 10 ตารางไม่มี PRIMARY KEY/UNIQUE/index แม้แต่ตัวเดียว; finance mode append ไม่มี dedupe

**ความเสี่ยง:** รัน append ซ้ำ = amount double count → งบประมาณบน dashboard สูงกว่าจริง

**ข้อเสนอ:** migration `003_add_constraints.sql` — PK บน `*_id` ของ master ทุกตัว → ทำได้เลย; natural key ของ `erp_2025` → **blocked ต้องให้ Domain Expert Finance ยืนยัน**

---

### G6 · [Data Architect] Schema source-of-truth กระจาย + migration runner ไม่มี tracking/dry-run — Data modeling, กติกาข้อ 5

**สถานะ:** finance ใกล้เคียง / research ไม่ตรงเลย — BQ DDL อยู่ที่ `src/research/publication/sql/` ไม่ใช่ `migrations/`; schema MSSQL track_evaluation ไม่มีใน repo เลย; `migrate.py` ไม่มีตาราง `schema_migrations` และไม่มี `--dry-run`

**ข้อเสนอ:** ย้าย DDL เป็น `migrations/research/bigquery/001_*.sql`, reverse-engineer MSSQL schema; เพิ่ม `schema_migrations` table + flag `--dry-run` (BEGIN…ROLLBACK) → ทำได้เลย

---

### G7 · [Security Engineer] Pipeline user ต้องมีสิทธิ์ DDL (TRUNCATE / DROP) — Security (Least Privilege)

**สถานะ:** ตรวจจาก repo ไม่ได้ / ไม่มี doc — โค้ดใช้ `TRUNCATE TABLE` และ pandas replace (DROP+CREATE) บังคับให้ user เดียวกันมีทั้ง DML และ DDL

**ความเสี่ยง:** credential หลุด → ผู้โจมตีลบตารางได้ทั้ง database

**ข้อเสนอ:** เปลี่ยน `TRUNCATE` → `DELETE FROM` (DML); เขียน `docs/db-roles.md` แยก `etl_writer` (INSERT/DELETE/SELECT) กับ `schema_owner` (รัน migration) → ทำได้เลย; ตรวจ grant จริง → **blocked รอ DBA**

---

### G8 · [Security Engineer + BI Engineer] PII (ชื่อนักวิจัย, cost_owner, score/reward รายบุคคล) ไม่มี access policy — Security (RBAC)

**สถานะ:** ใกล้เคียง — `firstname/lastname` อยู่ใน BQ `Research.publications` โดยตรง; view ตัดชื่อออกแล้ว ✓ แต่ไม่มี policy บังคับว่า dashboard ต้องอ่านผ่าน view นี้เท่านั้น

**ความเสี่ยง:** PDPA — ผู้ใช้ทุก role เห็นชื่อ + reward รายบุคคลของนักวิจัย

**ข้อเสนอ:** ทำ data classification table (column → public/internal/PII) → ทำได้เลย; BigQuery authorized views / policy tags + RBAC บน dashboard → **blocked รอเลือก tool + เจ้าของ access policy**

---

### G9 · [DevOps] Log ของ validator/loader หายจริง ไม่ถูกบันทึกลงไฟล์ — Observability

**สถานะ:** 🔄 **กำลังทำใน Phase 0** (planned commit `fix(logger): propagate submodule logs to shared 'src' logger`) — ต้องมี test ยืนยันว่า log ของ validator ขึ้นในไฟล์จริง

**ยังไม่ทำ:** แทน `print()` ด้วย logger ในจุดที่เหลือ (finance/master/migrate/connection ~30 จุด); เพิ่ม job summary line (job, rows_in, rows_out, duration, status) ท้ายทุก run → ทำได้เลย

---

### G10 · [Data Architect] erp_2025 ตั้งชื่อตามปี, type ไม่ตรงกับ master, ไม่มี reporting view / raw layer ใน DB — Data modeling, Data layering

**สถานะ:** ใกล้เคียง — มี `fiscal_year` column อยู่แล้วแต่ตารางชื่อ `erp_2025`; `erp_2025.ic_strategy/mu_strategy` เป็น NUMERIC แต่ `master_ic_strategy.ic_strategy_id` เป็น TEXT → join ไม่ได้ตรงๆ; ไม่มี FK; ไม่มี `v_finance_*` view

**ความเสี่ยง:** ปีงบ 2026 ต้องแก้โค้ด + migration + dashboard ใหม่ทั้งชุด

**ข้อเสนอ:** migration align type, สร้าง `v_finance_erp_report` join master; ทำเป็น `fact_erp` ที่ใช้ `fiscal_year` แยกแทนตารางต่อปี → **blocked บางส่วน รอ Finance ยืนยันว่า erp แต่ละปี structure เหมือนกันจริง**

---

## 🟡 MEDIUM

- **G11** · [Pipeline Engineer] Pattern extractor→transformer→validator→loader ไม่เป็นมาตรฐานเดียว (finance class-based, research function-based, zeal ไม่มี transformer/validator) → refactor research ให้มี extractor.py, เพิ่ม MasterValidator → ทำได้เลย
- **G12** · [BI Engineer] ไม่มี Metric Dictionary, ไม่ระบุ dashboard tool, business rule ใน view ไม่มีเอกสาร → `docs/metric-dictionary.md` skeleton → ทำได้เลย; นิยาม metric จริง → blocked รอเลือก tool
- **G13** · [Data Quality Engineer] ครอบคลุม DQ dimensions แค่ completeness/accuracy — ไม่มี consistency (referential check gl_id/cost_ctr_id กับ master), timeliness, uniqueness → เพิ่ม referential check ใน ErpValidator → ทำได้เลย
- **G14** · [DevOps] Environment ไม่ reproducible — dependency ไม่ pin version, ไม่มี Dockerfile, ไม่มี pyproject.toml, mdb-tools เป็น system dependency ที่ไม่ได้บันทึก → pin version + pyproject.toml + Dockerfile → ทำได้เลย
- **G15** · [Data Architect] นิยาม fiscal year อยู่ 2 ที่ (finance/research) implement แยกกัน, audit columns ไม่เท่ากันทุก DB → `helpers/fiscal.py` ตัวเดียว → ทำได้เลย
- **G16** · [Security Engineer] Secret hygiene พึ่ง gitignore อย่างเดียว, ไม่มี secret scanning, service account JSON อยู่ใน repo tree → pre-commit + gitleaks, ย้าย secrets ออกนอก repo tree → ทำได้เลย
- **G17** · [Pipeline Engineer] Hardcoded infra defaults (SSH_HOST, DB_NAME fallback) และ connection logic ซ้ำ 2-3 ที่ → รวมเป็น `helpers/connect_db/{postgres,mssql,bigquery}.py` → ทำได้เลย

## 🟢 LOW

- **G18** · [PM + ทุกคน] README 1 บรรทัด, docs เป็น HTML (diff/review ยาก), ไม่มี `docs/decisions/` → README quick-start + module map, decision log ผูกกับ migration → ทำได้เลย; ยืนยัน business rule ที่ยังไม่มีบันทึก (เช่น `fill_cost_owner`) → blocked รอ Domain Expert Finance
- **G19** · [Data Architect] Naming inconsistency (`master_io_activities` พหูพจน์ vs `master_io_goods/project/work` เอกพจน์) — รวมไปแก้พร้อม G10
- **G20** · [DevOps] `tests/test_connection.py` เป็น integration test ปนกับ unit test → ใส่ `@pytest.mark.integration` และ skip ใน CI → ทำได้เลย

---

## Roadmap (Project Manager)

### 🔄 Phase 0 — ทำทันทีก่อน upload รอบถัดไป (กำลังทำ)
G2 opt-in flag finance/zeal · G3 fail-fast track_evaluation · G9 fix logger propagate
→ กำลังทำบน branch `fix/phase0-production-write-safety` (แผน: 3 commits แยกตาม gap G9 → G3 → G2)
→ **ทำแล้ว (2026-09-17):** `.env` จริง reset เป็น false; test ค้างบน main แก้แล้ว (`3280f36`); `fill_cost_owner` แยกไป `feat/finance-fill-cost-owner` รอ Finance ยืนยัน; ODBC 17→18 แยกไป `fix/odbc-driver-18` รอ DevOps review

### Phase 1 — Sprint 1–2: ปิด critical gaps ด้าน quality/security
G1 CI + tests research · G4 shared prepare + reconciliation · G7 TRUNCATE→DELETE + `docs/db-roles.md` · G16 gitleaks/pre-commit · G6 schema_migrations + `--dry-run`
→ PM เริ่มไล่ blocked items คู่ขนาน: natural key ของ erp (Finance), source of truth MSSQL vs BQ (business owner), grant review (DBA), reward ว่าง = 0? (Research)

### Phase 2 — Sprint 3–4: architecture / modeling
G5 constraints migration · G10 align type + v_finance_* view · G6 ย้าย DDL research เข้า migrations · G11 unify pattern · G15 helpers/fiscal.py · G13 referential checks · G14 pyproject + Dockerfile
→ Data Architect เป็นเจ้าภาพ; ทุก schema change ผ่าน migration ใหม่ + decision log

### Phase 3 — observability / documentation / dashboard readiness
G12 Metric Dictionary + เลือก dashboard tool · G8 RBAC/authorized views · G17 รวม connection helpers · G18 README/decision log · G19/G20
→ BI Engineer + Security เป็นเจ้าภาพ; DevOps เช็ค pre-deployment checklist ซ้ำก่อน dashboard ขึ้น production ตามกติกาข้อ 7
