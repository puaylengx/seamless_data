# non-numeric score/weight ใน track_evaluation → NULL + WARNING (ไม่ fail)

- **วันที่:** 2026-09-17
- **อ้างอิง:** G3 · PR #1
- **ผู้ตัดสิน:** Project owner (ร่วมกับทีมเสมือน)

## การตัดสินใจ
ค่าที่ parse เป็นตัวเลขไม่ได้ใน weight/quality/contribution/score ของ track_evaluation กลายเป็น NULL แล้ว log WARNING พร้อมแถว Excel — ไม่ fail-fast

## เหตุผล
เป็น behavior เดิมของ path MSSQL อยู่แล้ว; reward ว่าง → 0 ยังรอ PD-2 จึงไม่เปลี่ยนนโยบายก่อนรู้ scope (บทเรียนจาก G3)

## สิ่งที่ยังค้าง / ทบทวนเมื่อ
ทบทวนพร้อม PD-2 — ถ้า Research ตอบว่า "ควร reject" ให้ย้ายเป็น validator rule

## ไฟล์/อาร์ติแฟกต์ที่เกี่ยว
`src/research/track_evaluation/transformer.py::coerce_and_clean` (TODO(PD-2))
