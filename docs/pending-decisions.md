# Pending Decisions — รอ input จากนอกทีม dev

> เจ้าภาพติดตาม: **Project Manager** (กติกาข้อ 7) · DevOps เช็คซ้ำก่อน deploy ว่าเงื่อนไขผ่านแล้วจริง
> อ้างอิงเลข gap จาก [`gap-analysis-2026-09.md`](gap-analysis-2026-09.md)
> เมื่อได้คำตอบ: ย้ายรายการไป `docs/decisions/YYYY-MM-DD-<slug>.md` พร้อมวันที่/เหตุผล และผูกกับ migration/commit ที่เกี่ยว
> **ชุดคำถามสำหรับฝ่ายการเงิน (PD-1, 3, 11a/b/c, 12, 13) เขียนแบบไม่ต้องรู้โค้ด:** [`finance-questions-2026-09.md`](finance-questions-2026-09.md) — PM ส่ง 2026-09-18; PD-10 ยังไม่ส่ง (ไฟล์ปัจจุบัน mismatch 0)

| # | เรื่อง | ถามใคร | สถานะ | เปิดเมื่อ |
|---|---|---|---|---|
| PD-1 | `fill_cost_owner` fallback | Domain Expert — Finance | ⏳ รอคำตอบ | 2026-09-17 |
| PD-2 | `reward` ว่าง/parse ไม่ได้ = 0 ? (G3) | Domain Expert — Research | ⏳ รอคำตอบ (โค้ดมี `TODO(PD-2)` แล้ว) | 2026-09-17 |
| PD-3 | natural key ของ `erp_2025` (G5) | Domain Expert — Finance | ⏳ รอคำตอบ | 2026-09-17 |
| PD-4 | source of truth: MSSQL vs BigQuery (G4) | Business owner ฝ่ายวิจัย | ⏳ รอคำตอบ | 2026-09-17 |
| PD-5 | grant จริงของ DB user ที่ pipeline ใช้ (G7/G8) — **รู้แล้วว่าเกินจำเป็น** ต้องการขอบเขตจริงเพื่อลดสิทธิ์ | DBA | ⏳ รอคำตอบ — query ตรวจเตรียมไว้แล้ว | 2026-09-17 |
| PD-6 | dashboard tool + เจ้าของ access policy (G8, G12) | หัวหน้าทีม / ผู้ใช้ dashboard | ⏳ รอคำตอบ | 2026-09-17 |
| PD-7 | ลบ backup tags `backup/pre-rewrite/*` (17 tags, local เท่านั้น) | Project owner สั่งเอง | ⏳ **ครบกำหนด 2026-09-24** — ห้ามลบอัตโนมัติ | 2026-09-17 |
| PD-8 | Publication: Year suffix + รายการ rank ที่ถูกต้อง (G21) | Domain Expert — Research | ⏳ รอคำตอบ | 2026-09-17 |
| PD-9 | DB จริงอยู่ที่ไหน — **ทั้ง MSSQL research และ PostgreSQL finance** (`.env` ชี้ localhost/VM ที่ไม่ตอบ) | DevOps / คนตั้งค่า `.env` เดิม | ⏳ รอคำตอบ — บล็อก G6 MSSQL DDL **และ** การตรวจ grant PD-5 | 2026-09-18 |
| PD-10 | fiscal_year จาก Excel ≠ derive จาก doc_date — จะ fail / ยึด doc_date / ยึด Excel (G15) | Domain Expert — Finance (หลังมีสถิติจาก log 2–3 รอบ) | ⏳ รอข้อมูลจริงก่อน แล้วรอคำตอบ | 2026-09-18 |
| PD-11a | master `status`: นิยาม/ค่าที่ถูกต้องต่อตาราง (G11) | Domain Expert — Finance | ⏳ รอคำตอบ | 2026-09-18 |
| PD-11b | `io_good_id 76530045` ซ้ำ 2 แถวเหมือนกัน — ลบ 1 แถวได้ไหม (G5, migration 004) | Domain Expert — Finance | ⏳ รอคำตอบ — **บล็อก 003 บน DB ที่มีแถวซ้ำ** | 2026-09-18 |
| PD-11c | `Master_IO_Activity` ว่าง 0 แถว — ตั้งใจหรือไฟล์ผิด | Domain Expert — Finance | ⏳ รอคำตอบ | 2026-09-18 |
| PD-12 | `erp.funds_ctr` (3000–3008) เทียบกับ master ไหน — ไม่ใช่ `master_fund` (8 หลัก) (G13) | Domain Expert — Finance | ⏳ รอคำตอบ | 2026-09-18 |
| PD-13 | รหัสใน ERP 2025 ที่ไม่อยู่ใน master ปัจจุบัน (gl 9, io_goods 126, io_project 10, io_work 9) — ขอไฟล์ master ใหม่ (G13) | Domain Expert — Finance | ⏳ รอไฟล์ | 2026-09-18 |

---

## PD-1 · `fill_cost_owner` — cost_owner ว่างให้ fallback เป็น cost_ctr_id จริงหรือไม่

- **ถามใคร:** Domain Expert — Finance
- **ถามอะไร:** เมื่อแถวใน ERP Excel มี `Cost_Owner` ว่าง ควรเติมด้วยค่า `CostCtr_ID` ของแถวนั้นหรือไม่ หรือควรปล่อยว่าง / reject
- **ทำไมต้องถาม:** โค้ดนี้อยู่บน branch `feat/finance-fill-cost-owner` (commit `3b923e0`) **ยังไม่มี test และไม่มีบันทึกว่าฝ่ายการเงินขอ** — ถ้าเติมผิด dashboard จะรวมยอดเข้า owner ที่ไม่ใช่เจ้าของงบจริง
- **หลักฐานจากไฟล์จริง (2026-09-18):** cost_owner ว่าง **3,362/6,726 แถว (50%)**; ในแถวที่มีค่า cost_owner == cost_ctr_id เพียง **2%** (ส่วนใหญ่เป็น `C3001100`) → กฎ fallback นี้ขัดกับ pattern จริง — น้ำหนักเอียงไปทาง "ไม่ใช้" แต่รอ Finance ยืนยัน (ดู finance-questions C1)
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
- **หลักฐานจากไฟล์จริง (2026-09-18):** ไม่มีชุด column ไหน unique — doc_no+gl_id+cost_ctr_id+amount ยังซ้ำ 108 แถว (ต่างกันแค่ details เช่น ชื่อผู้รับรางวัล), รวม details แล้วเหลือซ้ำเป๊ะ 2 แถว (Excel 904–905) → ต้องถาม Finance ว่า ERP มี line item number ไหม (finance-questions B1)

## PD-4 · source of truth ระหว่าง MSSQL กับ BigQuery (G4)

- **ถามใคร:** Business owner ฝ่ายวิจัย (ผู้ใช้ตัวเลข publication / track evaluation)
- **ถามอะไร:** เมื่อสอง DB ไม่ตรงกัน ตัวไหนถือเป็นเลขอ้างอิง และอีกตัวมีไว้ทำอะไร (backup / ระบบเดิม / dashboard เท่านั้น)
- **ทำไมต้องถาม:** ปัจจุบัน MSSQL ใช้ `append` (ซ้ำได้) ส่วน BQ ใช้ `MERGE` (upsert) — semantics ต่างกันโดยออกแบบ reconciliation check ต้องรู้ว่าเทียบกับใคร

## PD-5 · grant จริงของ DB user ที่ pipeline ใช้ (G7 / G8)

- **ถามใคร:** DBA (PostgreSQL `ic_finance` / zeal, MSSQL research)
- **ถามอะไร:** user ใน `.env` มี privilege อะไรบ้างตอนนี้ และ **ใคร/role ไหนอีกที่ SELECT `erp_2025` ได้ตรงๆ** (ตาราง `details` มีชื่อบุคคลจริง = PII, ดู `data-classification.md`) แล้วแยก role `etl_writer` / `schema_owner` / `bi_reader` ตาม `db-roles.md`
- **สิ่งที่รู้แน่จากโค้ดแล้ว (2026-09-18) — ไม่ใช่แค่ "ช่วยดู grant หน่อย":** user เดียวกันรันทั้ง pipeline และ `migrations/migrate.py` (สร้างตารางได้ → มี **CREATE/DDL**) และก่อน G7 โค้ดรัน `TRUNCATE TABLE` สำเร็จ (→ มี **TRUNCATE** ซึ่งปกติเป็นของ owner) ⇒ user นี้**มีสิทธิ์เกินความจำเป็นแน่นอน** สำหรับงาน INSERT/DELETE/SELECT; ที่ต้องการจาก DBA คือ**ขอบเขตจริง** (superuser? owner? มี role อื่นแชร์ตารางไหม) เพื่อลดสิทธิ์ให้ตรง `db-roles.md`
- **ทำไมยังไม่ตรวจเอง:** ตรวจจาก repo ไม่ได้ และ DB ที่ `.env` ชี้ต่อไม่ได้ ณ 2026-09-18 (ดู PD-9) — ทีมพยายามแล้ว 2 ทาง (direct localhost:5432 → refused, SSH 192.168.x.x:22 → ไม่ตอบ)
- **Query ที่ทีมจะรัน (หรือ DBA รันให้ได้เลย) — อ่าน catalog อย่างเดียว ไม่แตะข้อมูล, `SET default_transaction_read_only = on`:**

```sql
-- 1) ใครมีสิทธิ์อะไรบน erp_2025 (รวม PUBLIC)
SELECT grantee, privilege_type, is_grantable
  FROM information_schema.table_privileges
 WHERE table_schema = current_schema() AND table_name = 'erp_2025' ORDER BY 1, 2;

-- 2) owner + ACL ดิบ (จับ grant ให้ PUBLIC / role กลุ่ม)
SELECT pg_get_userbyid(c.relowner) AS owner, c.relacl
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relname = 'erp_2025' AND n.nspname = current_schema();

-- 3) role ทั้งหมด: superuser? login ได้? เป็นสมาชิก role ไหน (สิทธิ์สืบทอด)
SELECT r.rolname, r.rolsuper, r.rolcanlogin, r.rolcreatedb, r.rolcreaterole,
       ARRAY(SELECT b.rolname FROM pg_auth_members m JOIN pg_roles b ON b.oid = m.roleid WHERE m.member = r.oid) AS member_of
  FROM pg_roles r WHERE r.rolname NOT LIKE 'pg\_%' ORDER BY 1;

-- 4) user ของ pipeline เอง
SELECT current_user, session_user,
       has_table_privilege(current_user, 'erp_2025', 'SELECT')   AS can_select,
       has_table_privilege(current_user, 'erp_2025', 'TRUNCATE') AS can_truncate,
       has_schema_privilege(current_user, current_schema(), 'CREATE') AS can_create;

-- 5) default privileges ที่จะทำให้ตารางใหม่เปิดกว้างอัตโนมัติ
SELECT defaclrole::regrole, defaclnamespace::regnamespace, defaclobjtype, defaclacl FROM pg_default_acl;
```
- **ผ่านเกณฑ์เมื่อ:** pipeline user ไม่ใช่ superuser/owner, ไม่มี TRUNCATE/CREATE; `erp_2025` ไม่มี grant ให้ `PUBLIC`; role ที่ SELECT ได้มีเฉพาะ `etl_writer` + `schema_owner` (BI ผ่าน view เท่านั้น — G8/G10)
- **ประเมิน exposure ปัจจุบัน (2026-09-18):** ไม่มี dashboard/BI ต่อ PostgreSQL อยู่ และ DB ไม่มีใครเข้าถึงได้เลยตอนนี้ (down) → ไม่ใช่เหตุฉุกเฉิน แต่คนที่เคยได้ `.env`/SSH key ชุดนี้อ่าน `details` ได้เต็มตาราง

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

## PD-9 · DB จริงอยู่ที่ไหน — MSSQL research **และ** PostgreSQL finance (G6 / PD-5 / G8)

- **ถามใคร:** DevOps เจ้าของ credential เดิม หรือคนที่ตั้งค่า `.env` ตอนแรก (ไม่ใช่ Project owner — ตอบเองไม่ได้) — **คำถามเดียวกัน คนเดียวกัน ถามพร้อมกันทั้งสอง DB**
- **MSSQL research:** `LOCAL_HOST=localhost` ใน `.env` ชี้ไปที่ MSSQL instance **บนเครื่องนี้** ซึ่งตอนนี้ **ไม่ได้รันอยู่** (ตรวจ 2026-09-18: port 1433 ไม่เปิด, ไม่มี docker container แม้ stopped, ไม่มี `sqlservr` process; มี `sqlcmd`/`mssql-tools18` ติดตั้งไว้) แต่มีหลักฐานว่าเคย upload ข้อมูลจริงเข้าไป (log `logs/research/*`)
- **PostgreSQL finance (เพิ่ม 2026-09-18):** `.env` ปัจจุบัน `DB_CONNECTION_MODE=direct` → `localhost:5432` (`ic_finance`) — **ไม่มีอะไรฟัง** (ไม่มี process/brew service, Docker daemon ไม่รัน) · ในไฟล์ยังมี `SSH_HOST=192.168.x.x` (vmnet ของ macOS = VM) แต่ port 22 **ไม่ตอบ** · การออกแบบเดิม (`.env.example` รุ่นแรก, `docs/database.html`, fallback `192.168.64.2` ที่ G17 เพิ่งลบ) บอกว่า DB จริงอยู่ใน **VM ผ่าน SSH tunnel** · ไม่พบ UTM/Parallels/multipass/lima ในเครื่อง → VM อาจอยู่เครื่องอื่น/ถูกลบ
- **ถามอะไร (ทั้งสอง DB):**
  1. DB จริงอยู่ที่ไหน — VM `192.168.64.x` ใช่ไหม ใครเป็นเจ้าของ/ดูแล ตอนนี้เปิดอยู่ไหม start ยังไง (image/volume) หรือมี host จริงอื่นที่ควรใส่ใน `.env` แทน
  2. ถ้าเป็น dev copy ที่หายไปแล้ว: ข้อมูลที่เคย upload (log ยืนยัน) ไปอยู่ที่ไหน — มีสำเนา/ backup ไหม
- **ทำไมต้องถาม:** (MSSQL) G6 ต้องบันทึก schema ปัจจุบันเป็น `migrations/research/mssql/001_*.sql` — query read-only เตรียมไว้แล้ว (PR #13) · (PostgreSQL) ต้องตรวจ grant/exposure ของ `erp_2025` ที่มี PII (PD-5, query เตรียมไว้แล้ว) และ apply migration 003 · ถ้า `.env` ชี้ผิดที่ทั้งสอง DB แปลว่า upload/reconcile/migrate ทุกอย่างที่ผ่านมาทำกับ instance ที่ไม่มีใครดูแล
- **สิ่งที่ตัดสินใจแล้ว:** **ห้าม start service/container เอง** แม้จะเจอวิธี — ถ้าเป็น DB จริงที่หายไปโดยไม่ตั้งใจ การ "แก้ให้" อาจทับสภาพที่ทีมอื่นตั้งใจปล่อยไว้ (Project owner 2026-09-18)
- **ผลเมื่อได้คำตอบ:** รันสคริปต์ metadata dump เดิม → เขียน `001_*.sql` → ให้ Project owner ตรวจก่อน (ไม่ apply ที่ไหน)

## PD-10 · fiscal_year / fiscal_month จาก Excel ไม่ตรงกับที่คำนวณจาก doc_date (G15)

- **ถามใคร:** Domain Expert — Finance
- **ถามอะไร:** เมื่อไฟล์ ERP ระบุ `fiscal_year`/`fiscal_month` ต่างจากที่นิยาม `helpers/fiscal.py` (ปีงบเริ่ม ต.ค.) คำนวณจาก `doc_date` ควร (1) **fail-fast** ไม่โหลด (2) **ยึด doc_date** คำนวณทับ หรือ (3) **ยึด Excel** เพราะฝ่ายการเงิน post ย้อนงวดโดยตั้งใจ
- **ทำไมยังไม่ถาม/ยังไม่ทำ:** เป็น check ใหม่ ([PR #15](https://github.com/puaylengx/seamless_data/pull/15)) ยังไม่มีข้อมูลว่าไฟล์จริง mismatch บ่อยแค่ไหน → ตอนนี้ `ErpValidator` แค่ **WARNING** (`result["warnings"]`) ไม่ block เพื่อไม่ทำผิดซ้ำแบบ G3 ที่ fail-fast ก่อนรู้ scope
- **สถิติรอบแรก (ไฟล์ clean_ERP_2025.xlsx, 2026-09-18):** fiscal_year mismatch 0 / fiscal_month mismatch 0 จาก 6,726 แถว → ยังไม่มีอะไรถาม
- **ขั้นตอน:** รัน finance pipeline จริง 2–3 รอบ → รวมสถิติ mismatch (จำนวน/สัดส่วน/รูปแบบ เช่น กระจุกที่เดือนไหน) จาก log → นำไปถาม Finance พร้อมตัวเลข → ตัดสิน → เปลี่ยน validator ตามผล + decision log
- **ผูกกับ:** G15 (tracker), G13 (DQ consistency), Metric Dictionary G12 (นิยามปีงบต้องอยู่ที่นั่นด้วย)

## PD-11 · master data — 3 คำถามแยกกัน ตอบได้ทีละข้อ ไม่ต้องรอครบ (G5 / G11)

พบจากไฟล์จริง (อ่าน Excel local 2026-09-18, ไม่แตะ DB) · ถามใคร: **Domain Expert — Finance** ทั้ง 3 ข้อ

### PD-11a · นิยาม `status` ต่อตาราง
- **พบ:** `master_io_work` = `use` / `cancel` · `master_ic_strategy`, `master_mu_strategy` = `0` / `1` · ตารางอื่นไม่มี column status (transformer เติม `active`) — และ `MasterTransformer.add_status` เติม `active` ให้ช่องว่างแม้ในตารางที่ใช้ `use/cancel` (พฤติกรรมเดิม ยังไม่แก้)
- **ถาม:** แต่ละค่าหมายถึงอะไร (`1` = ใช้งานอยู่?), ควร normalize เป็นชุดเดียว (`active/inactive`) ไหม, ช่องว่างควรเป็นอะไร
- **ตอนนี้:** `MasterValidator` เตือน (ไม่ block) เมื่อ status นอกชุดที่พบจริงต่อตาราง (`VALID_STATUS_BY_TABLE`)
- **เมื่อตอบ:** ปรับ validator/transformer + decision log

### PD-11b · แถวซ้ำ `io_good_id 76530045` — ลบได้ไหม
- **พบ:** `Master_IO_Goods_20230531.xlsx` แถว 46–47 "เครื่องคอมพิวเตอร์สำนักงาน" ซ้ำ 2 แถว **เหมือนกันทุก column**
- **ถาม:** ลบเหลือ 1 แถวได้ไหม (เป็นความผิดพลาดของไฟล์ ไม่ใช่ 2 รายการจริง?)
- **ตอนนี้:** `MasterValidator` **fail** ไฟล์นี้ (key ซ้ำ) → โหลดใหม่ไม่ผ่านจนกว่าจะแก้ไฟล์ · migration **003** (ADD PRIMARY KEY อย่างเดียว) จะ **fail + rollback** บน DB ที่ยังมีแถวซ้ำ — พิสูจน์แล้วบน PostgreSQL 16 ชั่วคราว 2026-09-18 ([PR #17](https://github.com/puaylengx/seamless_data/pull/17)) · migration **004** (`-- migrate: manual`, ลบเฉพาะแถวเหมือนกันเป๊ะ) เตรียมไว้ **ห้าม apply จนกว่าข้อนี้ตอบ**
- **เมื่อตอบ "ลบได้":** กรอกผู้ยืนยัน/วันที่ในหัวไฟล์ 004 → `migrate.py --only finance/004_dedupe_io_goods --dry-run` บน staging → apply → แล้วรัน 003 ตามปกติ · ขอไฟล์ io_goods ที่แก้แล้วจาก Finance ด้วย

### PD-11c · `Master_IO_Activity_20230531.xlsx` ไม่มีข้อมูล
- **พบ:** 0 แถวหลัง dropna → ตาราง `master_io_activities` ว่าง
- **ถาม:** ตั้งใจ (ยังไม่มี activity) หรือไฟล์ผิด/ตกหล่น
- **ตอนนี้:** ไม่กระทบ 003 (PK บนตารางว่างได้)

## PD-12 · `erp.funds_ctr` ควรเทียบกับ master ตารางไหน (G13)

- **ถามใคร:** Domain Expert — Finance
- **พบ:** `erp_2025.funds_ctr` มีค่า 4 หลัก `3000`–`3008` (9 ค่า, ทุกแถว) แต่ `master_fund.fund_id` เป็น 8 หลัก `10101001`… (9 ค่า) → **ไม่มีค่าตรงกันเลย** — น่าจะเป็นคนละแนวคิดใน SAP (Fund vs Funds Center) ไม่ใช่รหัสใหม่
- **ถาม:** funds_ctr คือ Funds Center ใช่ไหม มี master ของ Funds Center หรือไม่ (ยังไม่มีในไฟล์ที่ทีมได้รับ) หรือ `Master_FUND` คือ Fund คนละตาราง
- **ตอนนี้:** ถอด `funds_ctr` ออกจาก `ERP_REFERENCES` (ไม่ตรวจ) เพื่อไม่เตือนผิด 100% · ถ้ามี master Funds Center ให้เพิ่มไฟล์ + mapping + migration ตารางใหม่

## PD-13 · รหัสใน ERP 2025 ที่ยังไม่อยู่ใน master — ขอไฟล์ master รุ่นใหม่ (G13 ส่วน 🔒)

- **ถามใคร:** Domain Expert — Finance (ผู้ดูแล master data)
- **พบ (รัน ErpValidator กับไฟล์ ERP 2025 + master ในเครื่อง 2026-09-18, ไม่แตะ DB):** master ล่าสุดคือ 2022-11 … 2024-06 ส่วน ERP ถึง 2025-09 → รหัสที่ไม่อยู่ใน master: `gl_id` 9 รหัส/52 แถว (กลุ่ม `1203…`), `io_goods` 126 รหัส/148 แถว, `io_project` 10 รหัส/378 แถว, `io_work` 9 รหัส/9 แถว; `cost_ctr_id` ตรงครบ; `ic/mu_strategy` ใน ERP ว่างทั้งไฟล์; `io_activity` มี 866 แถวแต่ master ว่าง (PD-11c)
- **ถาม:** ขอไฟล์ master ทุกตารางรุ่นล่าสุด (โดยเฉพาะ GL, IO Goods, IO Project) และยืนยันว่ารหัสเหล่านี้ถูกต้อง (ไม่ใช่พิมพ์ผิดใน ERP)
- **ตอนนี้:** referential check เป็น **WARNING** (`strict_reference=False`) พร้อมรายการรหัส/แถว · เมื่อได้ master ใหม่และ warning เป็น 0 → เปิด `strict_reference=True` ให้ fail-fast (decision log)

---

## ตัดสินภายในทีมแล้ว

ย้ายไป [`docs/decisions/`](decisions/README.md) (หนึ่งไฟล์ต่อหนึ่งการตัดสินใจ — G18) · เมื่อ PD ข้อใดได้คำตอบ ให้สร้างไฟล์ใหม่ที่นั่นแล้วลบแถวจากตารางด้านบน
