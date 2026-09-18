# Metric Dictionary — seamless_data (G12)

> **หนึ่งชื่อ = หนึ่งความหมายทั้งองค์กร** · เจ้าภาพ: **BI / Dashboard Engineer** ร่วม Data Architect · ทุกการเปลี่ยนนิยาม = แก้ไฟล์นี้ + วันที่ + เหตุผล + PR (กติกาข้อ 5)
> สถานะ: **skeleton** — บันทึกเฉพาะนิยามที่**มีอยู่ในโค้ดจริงแล้ว** (อ้างไฟล์/ฟังก์ชัน) · เครื่องมือ dashboard และ refresh schedule ยังรอ PD-6 · metric ใหม่ต้องผ่าน reporting view ไม่ query raw table (กติกาข้อ 6)

## รูปแบบ entry

| field | ความหมาย |
|---|---|
| ชื่อ metric / field | ชื่อที่ใช้บน dashboard และในโค้ด |
| นิยาม (ภาษาคน) | คนที่ไม่รู้โค้ดอ่านแล้วเข้าใจ |
| สูตร / กฎ | อ้างไฟล์:ฟังก์ชันที่คำนวณ (source of truth) |
| field ต้นทาง | column ใน table/ไฟล์ |
| grain | นับต่ออะไร (ต่อผลงาน / ต่อรายการ ERP / ต่อปี) |
| สถานะ | ✅ ยืนยันแล้ว · 🟡 ตามโค้ดปัจจุบัน ยังไม่ผ่าน Domain Expert · 🔒 รอ PD |
| เปลี่ยนล่าสุด | วันที่ + เหตุผล + PR |

---

## 1. นิยามข้ามโดเมน

### FY · ปีงบประมาณ (fiscal_year / publication_budget_year)
- **นิยาม:** ปีงบประมาณเริ่ม **1 ตุลาคม** — รายการวันที่ ต.ค.–ธ.ค. ของปี Y นับเป็นปีงบ Y+1; ม.ค.–ก.ย. นับเป็นปีงบ Y (เช่น 3 ธ.ค. 2024 → FY2025)
- **สูตร:** `helpers/fiscal.py::fiscal_year(year, month)` · `fiscal_year_from_date(date)` · `FISCAL_YEAR_START_MONTH = 10`
- **ใช้โดย:** finance `ErpTransformer.add_fiscal_month` (fiscal_month 1 = ต.ค.) · research `get_clean_budget_year`
- **กรณีขอบ:** เดือนว่าง → ใช้ปีปฏิทิน (พฤติกรรมเดิม research) · ปีว่าง → ว่าง
- **สถานะ:** ✅ นิยามเดียวทั้งโปรเจกต์ตั้งแต่ G15 (2026-09-18, PR #15) · 🔒 ค่าใน Excel ไม่ตรง doc_date จะ fail/ยึดอะไร → PD-10
- **ห้าม:** ปน FY กับปีปฏิทินบน chart เดียวกันโดยไม่ระบุ (Domain Expert Finance flag)

### as-of / ความสด (timeliness)
- **นิยาม:** ข้อมูล finance บน dashboard "ล่าสุดถึง" = `max(doc_date)` ของไฟล์ที่โหลด; master "รุ่นวันที่" = วันที่ในชื่อไฟล์ (`Master_GL_20230531`)
- **สูตร:** `ErpValidator.validate_timeliness` (เตือนเมื่อข้อมูล > 120 วัน / master > 365 วัน — ค่าเริ่มต้น ยังไม่มี SLA ตกลง)
- **สถานะ:** 🟡 · refresh schedule ของ dashboard ต้องตรงกับความถี่ที่ pipeline รันจริง (manual CLI ตอนนี้ ≠ real-time) → รอ PD-6

---

## 2. Finance (erp_2025 → PostgreSQL)

| field | นิยาม | สูตร/ที่มา | สถานะ |
|---|---|---|---|
| `amount` | จำนวนเงินของรายการ ERP (บาท, 2 ตำแหน่ง) — เครื่องหมายตาม ERP ไม่ปรับ | `ErpTransformer.convert_amount` (ลบ comma → numeric → round 2) | 🟡 ยังไม่ยืนยันว่าเป็น debit/credit หรือ net |
| `fiscal_year`, `fiscal_month`, `trimester` | ตามไฟล์ ERP (`Year`, `Trimester`) + คำนวณ fiscal_month จาก `month` | ดู FY ด้านบน · `trimester` มาจากไฟล์ตรงๆ ไม่มีนิยามในโค้ด | 🟡 trimester ต้องถาม Finance (นับจาก FY?) |
| `cost_ctr_id` / `cost_owner` | หน่วยงานเจ้าของรายการ / เจ้าของงบ | ไฟล์ ERP; `cost_owner` ว่าง 50% | 🔒 PD-1 |
| `gl_id` → กลุ่มบัญชี | รายการจัดกลุ่มตาม `master_gl.group_id` | join `erp_2025.gl_id = master_gl.gl_id` (referential check G13) | 🟡 GL ใหม่ 9 รหัสยังไม่อยู่ใน master → PD-13 |
| `funds_ctr` | Funds Center 3000–3008 | **ยังไม่มี master ที่ตรง** | 🔒 PD-12 |
| **ยอดใช้จ่ายตาม cost center / GL / IO** | `SUM(amount)` grouped by มิติ ภายใน FY | ยังไม่มี reporting view (`v_finance_*` — G10) · ห้ามสร้าง metric จาก raw table ตรง | 🔒 G10 + ต้องมี natural key กันนับซ้ำ (PD-3) |

---

## 3. Research — Publication (BigQuery `Research.publications`, MSSQL)

| field / metric | นิยาม | สูตร/ที่มา | สถานะ |
|---|---|---|---|
| `product_code` | รหัสผลงาน (ควร unique ต่อผลงาน) | ไฟล์ต้นทาง | 🟡 ซ้ำได้เมื่อผู้เขียนหลายคน — grain คือ "ผู้เขียน×ผลงาน" |
| `wos_*`, `scopus_q1..q4`, `scopus_sjr_10`, `tci_group1/2`, `national_journal`, ฐานอื่น | flag 0/1 ว่าผลงานอยู่ในฐาน/ควอไทล์นั้น parse จากข้อความ `Database (WoS, Scopus, TCI)` | `src/research/publication/transformer.py::_parse_database_entry` — กฎ: `JIF-P≥90` → `wos_with_jif_p90`; `Scimago r/N` กับ `r ≤ 0.1N` → `scopus_sjr_10`; TCI "Group 1/2" ไม่สนช่องว่าง/ตัวพิมพ์ | 🟡 ตามโค้ด · เกณฑ์ TCI/Scopus เปลี่ยนจากภายนอกต้องแจ้ง (Domain Expert Research) |
| `national_international` | ระดับผลงาน | `get_national_international`: ค่าจาก column classification ถ้ามี; "Being used as public policy"/"Featured role International venue"/"Group/International" → International; ว่าง → International ถ้ามี flag ฐานนานาชาติใดๆ ไม่งั้น National | 🟡 |
| `sdg1..sdg17` | ผลงานเชื่อม SDG ข้อใด (0/1) | `get_extract_sdg_values`: "3, 7.2, 18" → sdg3, sdg7 (เลขย่อย 7.2 นับเป็น 7; นอก 1–17 ทิ้ง) | 🟡 |
| `publication_year` / `publication_calendar_year` / `publication_budget_year` | ปีที่ตีพิมพ์ (calendar) / เท่ากันเสมอในโค้ดปัจจุบัน / ปีงบ (FY) | `get_clean_year` (ตัดอักขระที่ไม่ใช่ตัวเลข — เสี่ยง "2023 (RC3)" → 20233, validator จับช่วง 2000–2100) · `get_clean_budget_year` = FY | 🟡 `calendar_year` ซ้ำกับ `year` — ควรตัดหรือให้นิยามต่าง · 🔒 PD-8 |
| `effective_date` | วันที่มีผล = Online Date ถ้ามี ไม่งั้น Publication Date; "March 2024" → วันสิ้นเดือน | `get_format_effective_date` | 🟡 |
| `rank` / `group_rank` | ตำแหน่งวิชาการ (normalize "Asst.Prof" → "Asst.Prof.") / กลุ่ม: Academic Advisor, Support Staff, อื่นๆ = Lecturer | `get_rank`, `get_group_rank` | 🔒 รายการ rank ที่ถูกต้อง PD-8 |
| **จำนวนผลงานต่อปี (distinct)** | นับ `product_code` ไม่ซ้ำต่อ `publication_calendar_year` โดยเอาแถวปีล่าสุดของแต่ละ product_code | view `migrations/research/bigquery/002_*.sql` (`ROW_NUMBER() … ORDER BY calendar_year DESC, budget_year DESC` → `rn = 1`, `calendar_year >= 2017`) | 🟡 business rule นี้ไม่มีเอกสารที่อื่น — Domain Expert Research ยืนยัน |

---

## 4. Research — Track Evaluation (MSSQL, BigQuery)

| field | นิยาม | สูตร/ที่มา | สถานะ |
|---|---|---|---|
| `weight`, `quality`, `contribution`, `score` | น้ำหนัก/คุณภาพ/สัดส่วน/คะแนน — **มาจากไฟล์ที่ฝ่ายวิจัยคำนวณแล้ว** ระบบไม่คำนวณเอง ปัดทศนิยม 2 ตำแหน่ง | `coerce_and_clean` (round 2; non-numeric → NULL + WARNING) | 🟡 สูตรจริงอยู่นอกระบบ — ต้องบันทึกที่นี่เมื่อได้จาก Research |
| `reward` | เงินรางวัล (บาท) · ว่าง → 0 | `coerce_and_clean` (`fillna(0)`) | 🔒 PD-2 |
| `order_num` | เดือน (1–12) ของวันที่ตีพิมพ์ ใช้เรียงลำดับ | เติมจาก `publication_date` ถ้าว่าง | 🟡 |
| `corresponding` | ผู้เขียน corresponding (Yes/No/ว่าง) | title-case normalize | 🟡 |
| **รายการเดียวกัน (MERGE key)** | `product_code + publication_year + order_num + firstname + lastname + title` | `loader.MERGE_KEYS` — ใช้ทั้ง BigQuery MERGE และ reconcile | ✅ ตามโค้ด (2026-09-18, PR #9) |

---

## 5. ยังไม่มีนิยาม (ห้ามใช้บน dashboard จนกว่าจะเติม)
- Zeal Data ทุกตาราง (bronze/raw จาก .mdb — ยังไม่มี transformation)
- KPI รวมข้ามโดเมน (เช่น งบวิจัยต่อผลงาน) — ต้องนิยาม join key และ FY เดียวกันก่อน

## เปลี่ยนแปลง
| วันที่ | เรื่อง | เหตุผล | PR |
|---|---|---|---|
| 2026-09-18 | สร้าง skeleton จากนิยามที่มีในโค้ด | G12 ส่วนที่ไม่รอ PD-6 | — |
