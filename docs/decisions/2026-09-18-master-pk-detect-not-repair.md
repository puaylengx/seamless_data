# migration 003 = ADD PRIMARY KEY อย่างเดียว; การลบแถวซ้ำแยกเป็น 004 (manual)

- **วันที่:** 2026-09-18
- **อ้างอิง:** G5 · PR #17
- **ผู้ตัดสิน:** Project owner (ร่วมกับทีมเสมือน)

## การตัดสินใจ
003 ไม่มี DML — ถ้ามี key ซ้ำ PK fail → rollback ทั้ง transaction (พิสูจน์บน PostgreSQL 16 ชั่วคราว); 004 มี `-- migrate: manual` apply ได้เฉพาะ `--only` หลัง PD-11b

## เหตุผล
การลบข้อมูลจริงบน production (แม้ซ้ำเป๊ะ) ต้องเป็น explicit action ที่มีคนยืนยัน ไม่ฝังกับการเพิ่ม constraint

## สิ่งที่ยังค้าง / ทบทวนเมื่อ
PD-11b

## ไฟล์/อาร์ติแฟกต์ที่เกี่ยว
`migrations/finance/003_*.sql`, `004_*.sql`, `migrations/migrate.py` (manual marker)
