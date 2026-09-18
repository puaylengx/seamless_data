# prepare_for_load คง typed dtypes; object/None เฉพาะ MSSQL path

- **วันที่:** 2026-09-18
- **อ้างอิง:** G4 · PR #9
- **ผู้ตัดสิน:** Project owner (ร่วมกับทีมเสมือน)

## การตัดสินใจ
`prepare_for_load()` คืน Int64/string/date; `_for_pyodbc()` แปลงเป็น object/None เฉพาะก่อน `to_sql` ของ MSSQL

## เหตุผล
BigQuery path เดิมใช้ typed dtypes และพิสูจน์บน prod แล้ว; เปลี่ยนโดยไม่มี integration test = ความเสี่ยงที่ตรวจไม่ได้ (DRY ไม่คุ้ม)

## สิ่งที่ยังค้าง / ทบทวนเมื่อ
—

## ไฟล์/อาร์ติแฟกต์ที่เกี่ยว
`src/research/track_evaluation/loader.py`
