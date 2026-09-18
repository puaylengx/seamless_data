# reconcile ตรวจแถวซ้ำจาก rows > distinct ของปลายทาง ไม่ใช่จากขนาด batch

- **วันที่:** 2026-09-18
- **อ้างอิง:** G4 · PR #9
- **ผู้ตัดสิน:** Project owner (ร่วมกับทีมเสมือน)

## การตัดสินใจ
WARNING เมื่อปลายทาง rows > distinct MERGE_KEYS ในปีนั้น; ปลายทางมีมากกว่า batch แต่ไม่ซ้ำ = INFO (สะสมจาก upload ก่อนหน้า)

## เหตุผล
เทียบกับขนาด batch จะ false positive ทุกครั้งที่ทยอย upload ปีเดียวกันโดยตั้งใจ; ไม่ใช้ threshold เพราะซ้ำ 1 แถว = double count จริง

## สิ่งที่ยังค้าง / ทบทวนเมื่อ
SoT ยังรอ PD-4

## ไฟล์/อาร์ติแฟกต์ที่เกี่ยว
`src/research/reconcile.py::compare`
