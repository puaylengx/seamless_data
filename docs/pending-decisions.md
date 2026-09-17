# Pending Decisions — รอ input จากนอกทีม dev

> เจ้าภาพติดตาม: **Project Manager** (กติกาข้อ 7) · DevOps เช็คซ้ำก่อน deploy ว่าเงื่อนไขผ่านแล้วจริง
> อ้างอิงเลข gap จาก [`gap-analysis-2026-09.md`](gap-analysis-2026-09.md)
> เมื่อได้คำตอบ: ย้ายรายการไป `docs/decisions/YYYY-MM-DD-<slug>.md` พร้อมวันที่/เหตุผล และผูกกับ migration/commit ที่เกี่ยว

| # | เรื่อง | ถามใคร | สถานะ | เปิดเมื่อ |
|---|---|---|---|---|
| PD-1 | `fill_cost_owner` fallback | Domain Expert — Finance | ⏳ รอคำตอบ | 2026-09-17 |
| PD-2 | `reward` ว่าง/parse ไม่ได้ = 0 ? (G3) | Domain Expert — Research | ⏳ รอคำตอบ | 2026-09-17 |
| PD-3 | natural key ของ `erp_2025` (G5) | Domain Expert — Finance | ⏳ รอคำตอบ | 2026-09-17 |
| PD-4 | source of truth: MSSQL vs BigQuery (G4) | Business owner ฝ่ายวิจัย | ⏳ รอคำตอบ | 2026-09-17 |
| PD-5 | grant จริงของ DB user ที่ pipeline ใช้ (G7) | DBA | ⏳ รอคำตอบ | 2026-09-17 |
| PD-6 | dashboard tool + เจ้าของ access policy (G8, G12) | หัวหน้าทีม / ผู้ใช้ dashboard | ⏳ รอคำตอบ | 2026-09-17 |

---

## PD-1 · `fill_cost_owner` — cost_owner ว่างให้ fallback เป็น cost_ctr_id จริงหรือไม่

- **ถามใคร:** Domain Expert — Finance
- **ถามอะไร:** เมื่อแถวใน ERP Excel มี `Cost_Owner` ว่าง ควรเติมด้วยค่า `CostCtr_ID` ของแถวนั้นหรือไม่ หรือควรปล่อยว่าง / reject
- **ทำไมต้องถาม:** โค้ดนี้อยู่บน branch `feat/finance-fill-cost-owner` (commit `1abe498`) **ยังไม่มี test และไม่มีบันทึกว่าฝ่ายการเงินขอ** — ถ้าเติมผิด dashboard จะรวมยอดเข้า owner ที่ไม่ใช่เจ้าของงบจริง
- **ผลถ้าตอบ "ใช่":** เขียน `test_fill_cost_owner` + decision log แล้ว PR เข้า main
- **ผลถ้าตอบ "ไม่":** ลบ branch ทิ้ง

## PD-2 · `reward` ที่ parse เป็นตัวเลขไม่ได้ → 0 (G3)

- **ถามใคร:** Domain Expert — Research
- **ถามอะไร:** ใน track_evaluation ค่า `REWARD` ที่ว่างหรือไม่ใช่ตัวเลข ปัจจุบันถูกแทนด้วย 0 ก่อน insert — ถูกต้องตามเกณฑ์จริงหรือควร reject แถวนั้นให้คนแก้ไฟล์ก่อน
- **ทำไมต้องถาม:** reward เป็นเงินจริงที่จ่ายนักวิชาการ การแทน 0 เงียบๆ = จ่ายขาด; Phase 0 คง behavior เดิมไว้พร้อม `TODO` ในโค้ด (`coerce_and_clean`)

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
