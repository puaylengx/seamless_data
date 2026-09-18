# Data Classification — column ไหนเป็น PII / ข้อมูลอ่อนไหว และต้องคุมอย่างไรก่อนขึ้น dashboard (G8)

> เจ้าภาพ: **Security & Compliance Engineer** ร่วม BI Engineer · อ้างอิง PDPA + Principle of Least Privilege
> สถานะ: **ตารางจำแนกเสร็จ (ทำได้เลย)** · การบังคับใช้จริง (authorized view / policy tag / RBAC บน dashboard) รอ **PD-6** (เครื่องมือ dashboard + เจ้าของ access policy)

## ระดับ

| ระดับ | ความหมาย | กฎ |
|---|---|---|
| **P** Public-internal | ทุกคนในองค์กรที่เข้า dashboard เห็นได้ | ผ่าน reporting view |
| **I** Internal | เห็นเฉพาะทีมงาน/ผู้บริหารที่เกี่ยว (ตัวเลขการเงินรายรายการ) | view แยกตาม role |
| **PII** | ระบุตัวบุคคลได้ (ชื่อ-นามสกุล, ชื่อในคำอธิบายรายการ) | **ห้าม** อยู่ใน view ที่คนหลาย role เข้าถึง; ให้ aggregate หรือใช้รหัสแทน |
| **S** Sensitive | เงินรายบุคคล (รางวัล/คะแนนประเมิน) | เห็นเฉพาะเจ้าของข้อมูล + ผู้มีอำนาจ; audit log การเข้าถึง |

## Finance — `erp_2025` (PostgreSQL)

| column | ระดับ | หมายเหตุ |
|---|---|---|
| `fiscal_year`, `fiscal_month`, `trimester`, `day`, `month`, `year`, `doc_date` | P | |
| `doc_no` | I | เลขเอกสาร ERP — ใช้ตรวจสอบย้อน ไม่จำเป็นบน dashboard |
| `funds_ctr`, `cost_ctr_id`, `gl_id`, `gl_description`, `io_*`, `mu_strategy`, `ic_strategy` | P | รหัส/ชื่อหน่วยงาน-บัญชี-โครงการ |
| `cost_owner` | I | รหัสหน่วยงานเจ้าของงบ (ไม่ใช่บุคคล) |
| `amount` | I | ยอดรายรายการ — aggregate ต่อ cost center/GL/FY ถือเป็น P |
| `cost_note`, `order_description` | I | ข้อความอิสระ — อาจมีชื่อโครงการ/ผู้เกี่ยวข้อง → ตรวจก่อนแสดง |
| **`details`** | **PII** | ข้อความรายการมี**ชื่อบุคคล**จริง (เช่น "เงินรางวัลผลงานตีพิมพ์-<ชื่อ>", "ค่าตอบแทนกรรมการ…<ชื่อ>") — **ห้ามขึ้น dashboard ทั่วไป** ให้แสดงเฉพาะ drill-down ที่มีสิทธิ์ |
| `created_at/by`, `updated_at/by` | I | audit column; `created_by` เป็นชื่อผู้รัน pipeline |

**master_*** — ทุก column เป็น **P** (รหัสและชื่อหน่วยงาน/บัญชี/โครงการ ไม่มีบุคคล)

## Research — `publications` (BigQuery `Research.publications`, MSSQL)

| column | ระดับ | หมายเหตุ |
|---|---|---|
| **`firstname`, `lastname`** | **PII** | ชื่อนักวิจัย — view สาธารณะต้องตัดออก (view `002_create_view_publication_db_group_product_code` ตัดแล้ว ✓) |
| `title`, `source`, `volume`, `issue`, `pages` | P | ข้อมูลผลงานตีพิมพ์เป็นสาธารณะโดยธรรมชาติ แต่ `title` + ชื่อ = ระบุบุคคลได้ → ใน view ที่ไม่มีชื่อ ยังตามหาเจ้าของได้ผ่านการค้นภายนอก — ยอมรับได้ (ข้อมูลตีพิมพ์เผยแพร่อยู่แล้ว) |
| `product_code` | I | รหัสภายใน |
| `rank`, `group_rank`, `division`, `description` | P (aggregate) / I (รายแถว) | rank + division + ปี อาจชี้ตัวคนได้ในหน่วยงานเล็ก → แสดงเป็นจำนวนนับเท่านั้นเมื่อ n < 5 (k-anonymity ขั้นต่ำ) |
| flag ฐานข้อมูล (`wos_*`, `scopus_*`, `tci_*`, …), `sdg1..17`, ปี, `effective_date`, `national_international`, `field` | P | |

## Research — `track_evaluation` (MSSQL, BigQuery)

| column | ระดับ | หมายเหตุ |
|---|---|---|
| **`firstname`, `lastname`** | **PII** | |
| **`score`, `weight`, `quality`, `contribution`** | **S** | คะแนนประเมินรายบุคคล |
| **`reward`** | **S** | เงินรางวัลรายบุคคล (บาท) — ห้ามแสดงรายคนนอกเจ้าของ/ผู้อนุมัติ; รวมต่อ division/ปี = I |
| `corresponding`, `rc_meeting`, `order_num`, `publication_year/month/date`, `rank`, `division`, `description`, `title`, `source`, `product_code` | P/I | ดูกฎ n < 5 เหมือน publications |

## Zeal Data (PostgreSQL, raw จาก .mdb)
- **ยังไม่จำแนก** — module ยังไม่อยู่บน main และตารางถูกสร้างจากไฟล์ .mdb โดยตรง (Data/Inven/Lang/Report/Setting/Sys) · ต้องดูรายตารางเมื่อ merge; ชื่อไฟล์ "Setting"/"Sys" อาจมี credential ของระบบต้นทาง → **ห้ามส่งขึ้น dashboard ก่อนตรวจ**

## กฎที่ใช้ได้ทันที (ไม่รอ PD-6)
1. dashboard/BI **query ได้เฉพาะ reporting view** (`v_*`) ไม่ใช่ raw table (กติกาข้อ 6) — view ต้องไม่มี column ระดับ PII/S
2. metric รายบุคคล (S) แสดงได้เฉพาะ view ที่ผูก role และมี access log
3. ข้อความอิสระ (`details`, `cost_note`, `order_description`) ไม่ขึ้น dashboard ทั่วไป
4. จำนวนนับต่อกลุ่มเล็ก (< 5 คน) ให้รวมกลุ่มหรือซ่อน

## ที่ต้องทำเมื่อ PD-6 ตอบ (เลือกเครื่องมือ + เจ้าของ policy)
- **BigQuery:** authorized views ต่อ role (`bi_reader` เห็นเฉพาะ view) หรือ policy tags บน `firstname/lastname/reward/score`; service account ของ dashboard = `dataViewer` บน view dataset เท่านั้น (ดู `db-roles.md`)
- **PostgreSQL:** role `bi_reader` GRANT SELECT เฉพาะ `v_finance_*` (G10) ไม่ใช่ `erp_2025`
- **MSSQL:** view + `db_datareader` เฉพาะ schema ของ view
- Dashboard tool: row-level security ตาม division ถ้ารองรับ; access log ตรวจเป็นกิจวัตร (pre-production checklist ของ Security)
