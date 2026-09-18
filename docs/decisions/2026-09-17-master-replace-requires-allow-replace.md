# MasterLoader default mode=replace ต้อง opt-in ALLOW_REPLACE

- **วันที่:** 2026-09-17
- **อ้างอิง:** G2 · PR #1
- **ผู้ตัดสิน:** Project owner (ร่วมกับทีมเสมือน)

## การตัดสินใจ
`python src/finance/master/main.py` (default replace) error ทันทีถ้าไม่ตั้ง `ALLOW_REPLACE=true`

## เหตุผล
กติกา security-by-default ข้อ 2 — การล้างตารางต้องเป็น explicit action; UX เปลี่ยนโดยตั้งใจ (README)

## สิ่งที่ยังค้าง / ทบทวนเมื่อ
—

## ไฟล์/อาร์ติแฟกต์ที่เกี่ยว
`helpers/replace_guard.py`, README
