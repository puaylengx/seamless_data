# guard ALLOW_REPLACE รวมเป็น helper เดียว

- **วันที่:** 2026-09-17
- **อ้างอิง:** G2 · PR #1/#2
- **ผู้ตัดสิน:** Project owner (ร่วมกับทีมเสมือน)

## การตัดสินใจ
`helpers/replace_guard.py::ensure_replace_allowed(context)` ตัวเดียว ทุก loader (finance ERP/master, zeal) import ร่วม

## เหตุผล
กติกาข้อ 3 validation/guard อยู่จุดเดียว ไม่ copy ต่อ module

## สิ่งที่ยังค้าง / ทบทวนเมื่อ
—

## ไฟล์/อาร์ติแฟกต์ที่เกี่ยว
`helpers/replace_guard.py`
