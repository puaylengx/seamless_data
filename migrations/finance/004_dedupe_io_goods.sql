-- migration: 004_dedupe_io_goods  (G5 / PD-11)
-- migrate: manual
--
-- ⛔ ห้าม apply จนกว่า PD-11 (io_goods 76530045) จะได้คำตอบจาก Domain Expert Finance ว่าลบได้
--    ดู docs/pending-decisions.md — เมื่อตอบแล้วให้บันทึกวันที่/ผู้ยืนยันไว้ในไฟล์นี้ก่อน apply
--
-- ทำอะไร: ลบแถวใน master_io_goods ที่ **เหมือนกันทุก column** (io_good_id, io_good_description, status)
--          ให้เหลือ 1 แถวต่อ key — ไม่ตัดสินว่าแถวไหน "ถูก" ถ้า column อื่นต่างกันจะไม่ลบ
-- ทำไมแยกจาก 003: การลบข้อมูลจริงบน production (แม้จะซ้ำเป๊ะ) ต้องเป็น explicit action ที่มีคนยืนยัน
--                 ไม่ฝังไปกับการเพิ่ม constraint — 003 จะ fail ถ้าแถวซ้ำยังอยู่ ซึ่งเป็นสัญญาณให้มาดูไฟล์นี้
-- "-- migrate: manual" ด้านบน = migrations/migrate.py จะ **ข้าม** ไฟล์นี้เสมอ (แม้สั่ง all) และ apply ได้เฉพาะ
--   python migrations/migrate.py --only finance/004_dedupe_io_goods [--dry-run]
-- ลำดับเมื่อได้รับอนุญาต: --only 004 ก่อน แล้วค่อยรัน 003 ตามปกติ
--
-- PD-11 confirmed by: __________   date: __________

DELETE FROM master_io_goods a USING master_io_goods b
 WHERE a.ctid < b.ctid
   AND a.io_good_id          = b.io_good_id
   AND a.io_good_description IS NOT DISTINCT FROM b.io_good_description
   AND a.status              IS NOT DISTINCT FROM b.status;
