# Pending Decisions — รอ input จากนอกทีม dev

> เจ้าภาพติดตาม: **Project Manager** (กติกาข้อ 7) · DevOps เช็คซ้ำก่อน deploy ว่าเงื่อนไขผ่านแล้วจริง
> อ้างอิงเลข gap จาก [`gap-analysis-2026-09.md`](gap-analysis-2026-09.md)
> เมื่อได้คำตอบ: ย้ายรายการไป `docs/decisions/YYYY-MM-DD-<slug>.md` พร้อมวันที่/เหตุผล และผูกกับ migration/commit ที่เกี่ยว

| # | เรื่อง | ถามใคร | สถานะ | เปิดเมื่อ |
|---|---|---|---|---|
| PD-1 | `fill_cost_owner` fallback | Domain Expert — Finance | ⏳ รอคำตอบ | 2026-09-17 |
| PD-2 | `reward` ว่าง/parse ไม่ได้ = 0 ? (G3) | Domain Expert — Research | ⏳ รอคำตอบ (โค้ดมี `TODO(PD-2)` แล้ว) | 2026-09-17 |
| PD-3 | natural key ของ `erp_2025` (G5) | Domain Expert — Finance | ⏳ รอคำตอบ | 2026-09-17 |
| PD-4 | source of truth: MSSQL vs BigQuery (G4) | Business owner ฝ่ายวิจัย | ⏳ รอคำตอบ | 2026-09-17 |
| PD-5 | grant จริงของ DB user ที่ pipeline ใช้ (G7) | DBA | ⏳ รอคำตอบ | 2026-09-17 |
| PD-6 | dashboard tool + เจ้าของ access policy (G8, G12) | หัวหน้าทีม / ผู้ใช้ dashboard | ⏳ รอคำตอบ | 2026-09-17 |
| PD-7 | ลบ backup tags `backup/pre-rewrite/*` (17 tags, local เท่านั้น) | Project owner สั่งเอง | ⏳ **ครบกำหนด 2026-09-24** — ห้ามลบอัตโนมัติ | 2026-09-17 |
| PD-8 | Publication: Year suffix + รายการ rank ที่ถูกต้อง (G21) | Domain Expert — Research | ⏳ รอคำตอบ | 2026-09-17 |

---

## PD-1 · `fill_cost_owner` — cost_owner ว่างให้ fallback เป็น cost_ctr_id จริงหรือไม่

- **ถามใคร:** Domain Expert — Finance
- **ถามอะไร:** เมื่อแถวใน ERP Excel มี `Cost_Owner` ว่าง ควรเติมด้วยค่า `CostCtr_ID` ของแถวนั้นหรือไม่ หรือควรปล่อยว่าง / reject
- **ทำไมต้องถาม:** โค้ดนี้อยู่บน branch `feat/finance-fill-cost-owner` (commit `3b923e0`) **ยังไม่มี test และไม่มีบันทึกว่าฝ่ายการเงินขอ** — ถ้าเติมผิด dashboard จะรวมยอดเข้า owner ที่ไม่ใช่เจ้าของงบจริง
- **ผลถ้าตอบ "ใช่":** เขียน `test_fill_cost_owner` + decision log แล้ว PR เข้า main
- **ผลถ้าตอบ "ไม่":** ลบ branch ทิ้ง

## PD-2 · `reward` ที่ parse เป็นตัวเลขไม่ได้ → 0 (G3)

- **ถามใคร:** Domain Expert — Research
- **ถามอะไร:** ใน track_evaluation ค่า `REWARD` ที่ว่างหรือไม่ใช่ตัวเลข ปัจจุบันถูกแทนด้วย 0 ก่อน insert — ถูกต้องตามเกณฑ์จริงหรือควร reject แถวนั้นให้คนแก้ไฟล์ก่อน
- **ทำไมต้องถาม:** reward เป็นเงินจริงที่จ่ายนักวิชาการ การแทน 0 เงียบๆ = จ่ายขาด; Phase 0 ([PR #1](https://github.com/puaylengx/seamless_data/pull/1)) คง behavior เดิมไว้พร้อม `TODO(PD-2)` ใน `src/research/track_evaluation/transformer.py::coerce_and_clean`
- **ประเด็นพ่วง (ตัดสินภายในแล้ว 2026-09-17):** `score`/`weight`/`quality`/`contribution` ที่ non-numeric (เช่น "N/A") → NULL พร้อม WARNING ระบุแถว Excel ไม่ fail — PM ตัดสินให้คงไว้ก่อน ถ้าฝ่ายวิจัยตอบ PD-2 ว่า "ควร reject" ให้ทบทวน rule นี้พร้อมกัน
- **ผลถ้าตอบ "0 ถูกต้อง":** ลบ TODO, เพิ่ม test ยืนยัน, บันทึก decision log
- **ผลถ้าตอบ "ควร reject":** ย้ายจาก fillna(0) เป็น validator rule → fail-fast

## PD-3 · natural key ของ `erp_2025` (G5)

- **ถามใคร:** Domain Expert — Finance
- **ถามอะไร:** ชุด column ใดที่ระบุ "รายการเดียวกัน" ได้แน่นอนในไฟล์ ERP (เช่น `doc_no + gl_id + cost_ctr_id + amount`? หรือมี line item number ที่ยังไม่ได้ export)
- **ทำไมต้องถาม:** ต้องใช้สร้าง UNIQUE constraint / dedupe ให้ `append` รันซ้ำได้โดยไม่ double count — เดาเองผิด = ทิ้งแถวจริงหรือปล่อยแถวซ้ำ

## PD-4 · source of truth ระหว่าง MSSQL กับ BigQuery (G4)

- **ถามใคร:** Business owner ฝ่ายวิจัย (ผู้ใช้ตัวเลข publication / track evaluation)
- **ถามอะไร:** เมื่อสอง DB ไม่ตรงกัน ตัวไหนถือเป็นเลขอ้างอิง และอีกตัวมีไว้ทำอะไร (backup / ระบบเดิม / dashboard เท่านั้น)
- **ทำไมต้องถาม:** ปัจจุบัน MSSQL ใช้ `append` (ซ้ำได้) ส่วน BQ ใช้ `MERGE` (upsert) — semantics ต่างกันโดยออกแบบ reconciliation check ต้องรู้ว่าเทียบกับใคร

## PD-5 · grant จริงของ DB user ที่ pipeline ใช้ (G7)

- **ถามใคร:** DBA (PostgreSQL `ic_finance` / zeal, MSSQL research)
- **ถามอะไร:** user ใน `.env` มี privilege อะไรบ้างตอนนี้ (DDL? TRUNCATE? superuser?) และแยก role `etl_writer` / `schema_owner` ให้ได้ไหม
- **ทำไมต้องถาม:** ตรวจจาก repo ไม่ได้; ทีมแก้โค้ดให้ไม่ต้องใช้ DDL ได้ (TRUNCATE → DELETE) แต่ลดสิทธิ์จริงต้อง DBA ทำ

## PD-6 · dashboard tool และเจ้าของ access policy (G8, G12)

- **ถามใคร:** หัวหน้าทีม / ผู้ใช้ dashboard หลัก
- **ถามอะไร:** จะใช้เครื่องมืออะไร (Looker Studio / Power BI / Metabase / อื่น) และใครเป็นคนอนุมัติว่า role ไหนเห็นชื่อนักวิจัย + reward รายบุคคลได้
- **ทำไมต้องถาม:** RBAC / authorized view / refresh schedule / Metric Dictionary ออกแบบไม่ได้ถ้าไม่รู้เครื่องมือและเจ้าของ policy

## PD-7 · ลบ backup tags หลัง history rewrite — ครบกำหนด **2026-09-24**

- **ถามใคร:** Project owner (ไม่ใช่นอกทีม แต่ต้องสั่งเอง ห้าม Claude ลบอัตโนมัติ)
- **ถามอะไร:** หลัง 2026-09-24 (7 วันนับจาก rewrite) ถ้าไม่พบปัญหาแทรกซ้อนจากการ rewrite history วันที่ 2026-09-17 (16 commits remapped, ลบ trailer `Co-Authored-By: Claude`) ให้ลบ tag `backup/pre-rewrite/*` ทั้ง 17 ตัวด้วย `git tag -d $(git tag -l 'backup/pre-rewrite/*')`
- **ทำไมต้องรอ:** tag เหล่านี้ยังชี้ commit เดิม (SHA เก่า) ไว้ใช้ย้อนกลับได้ถ้า PR #2/#3/#4 หรือ main มีปัญหา; ผลข้างเคียงคือ `git log --all --grep="Co-Authored-By: Claude"` ยังเห็น 11 commit เดิมผ่าน tag เหล่านี้จนกว่าจะลบ (ใช้ `--branches --remotes` แทนจะได้ 0)
- **สำรองอื่นที่ไม่ได้อยู่ใน repo:** `~/Desktop/icit_project/icit_data/seamless_data-before-rewrite-2026-09-17.bundle` — ลบหรือเก็บต่อได้ตามสะดวก ไม่กระทบ repo
- **ผลเมื่อลบแล้ว:** ย้ายรายการนี้ไปตาราง "ตัดสินภายในทีมแล้ว" พร้อมวันที่

## PD-8 · Publication — Year suffix และรายการ rank ที่ถูกต้อง (G21)

- **ถามใคร:** Domain Expert — Research
- **ถามอะไร:**
  1. cell "Year" ในไฟล์ต้นทางมี suffix อื่นนอกจากตัวเลขล้วนได้ไหม (เช่น `"2023 (RC3)"`) — ถ้ามี ควร **reject** แถวนั้น หรือ **strip suffix** แล้วใช้ปี
  2. รายการ rank ที่ถูกต้องทั้งหมดคืออะไร — ตอนนี้ `_VALID_RANKS` มี 7 ค่า (Lecturer, Assoc.Prof., Support Staff, Asst.Prof., Prof., Asst.Lect., Academic Advisor) แต่ค่าที่ไม่อยู่ในรายการ (เช่น `"Dr."`) **หลุดผ่าน** ทุกชั้นโดยไม่ถูกตรวจ
- **ทำไมต้องถาม:** `get_clean_year` ลบทุกตัวที่ไม่ใช่ตัวเลข → `"2023 (RC3)"` กลายเป็น `20233` เงียบๆ และ validator เช็คแค่ > 0; ทั้ง `publication_year` และ `publication_budget_year` (ปีงบสำหรับ KPI) จะผิดตามโดยไม่มี error — พบระหว่างเขียน test ของ G1 ([PR #6](https://github.com/puaylengx/seamless_data/pull/6))
- **ทำได้เลยโดยไม่รอ:** เพิ่ม range check ปี (เช่น 2000–2100) ใน validator เพื่อจับ `20233` — ไม่ขึ้นกับคำตอบ
- **ผลเมื่อได้คำตอบ:** ปรับ `get_clean_year` (reject/strip) + เพิ่ม rank check ใน `validate_publication` + test ใน G21

---

## ตัดสินภายในทีมแล้ว (ไม่ต้องรอนอกทีม) — เก็บไว้เป็น audit trail จนกว่าจะมี `docs/decisions/`

| วันที่ | เรื่อง | ผล | อ้างอิง |
|---|---|---|---|
| 2026-09-17 | non-numeric `score`/`weight` ใน track_evaluation → NULL + WARNING หรือ fail? | คงเป็น WARNING (behavior เดิมของ path MSSQL) ผูกกับ PD-2 | G3, PR #1 |
| 2026-09-17 | `MasterLoader` default `mode="replace"` ต้อง opt-in `ALLOW_REPLACE` ด้วยหรือไม่ | ต้อง — `master/main.py` error โดยตั้งใจถ้าไม่ตั้ง flag (README) | G2, PR #1 |
| 2026-09-17 | guard `ALLOW_REPLACE` copy ต่อ module หรือรวม? | รวมเป็น `helpers/replace_guard.py` ตัวเดียว ทุก loader import ร่วม | G2, PR #1/#2 |
| 2026-09-17 | trailer `Co-Authored-By: Claude` ใน 11 commit ที่ push แล้ว | rewrite ทั้งหมดครั้งเดียวด้วย filter-repo (16 SHA เปลี่ยน, tree เท่าเดิม) + force-with-lease; กฎถาวรอยู่ใน CLAUDE.md | PR #3, PR #4 |
| 2026-09-17 | zeal_data half ของ G2 อยู่ branch ไหน | `fix/phase0-zeal-replace-guard` base `feat/aditayathorn-zeal-data` (module ยังไม่อยู่บน main) | PR #2 |
