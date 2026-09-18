# check ใหม่ (fiscal cross-check, referential, timeliness) เป็น WARNING ก่อน ไม่ fail-fast

- **วันที่:** 2026-09-18
- **อ้างอิง:** G13/G15 · PR #15, #18
- **ผู้ตัดสิน:** Project owner (ร่วมกับทีมเสมือน)

## การตัดสินใจ
`ErpValidator` คืน `warnings[]` แยกจาก `errors[]`; `strict_reference=True` เปิดเมื่อ master ครบ

## เหตุผล
บทเรียน G3: fail-fast ก่อนรู้ scope ของปัญหาในข้อมูลจริง = pipeline หยุดโดยไม่มีข้อมูลตัดสิน; เก็บสถิติก่อน (PD-10, PD-13)

## สิ่งที่ยังค้าง / ทบทวนเมื่อ
PD-10, PD-13

## ไฟล์/อาร์ติแฟกต์ที่เกี่ยว
`src/finance/validator.py`
