# rewrite git history ลบ trailer Co-Authored-By: Claude

- **วันที่:** 2026-09-17
- **อ้างอิง:** PR #3, #4
- **ผู้ตัดสิน:** Project owner (ร่วมกับทีมเสมือน)

## การตัดสินใจ
rewrite ทั้ง repo ครั้งเดียวด้วย `git filter-repo --refs=--branches` (16 SHA เปลี่ยน, tree เท่าเดิมทุก commit) + `--force-with-lease` ทุก branch ที่ push แล้ว; กฎถาวรใน `CLAUDE.md` + `docs/team-project-instructions.md`; backup tags `backup/pre-rewrite/*` เก็บถึง 2026-09-24 (PD-7)

## เหตุผล
เจ้าของโปรเจกต์ต้องการ history ที่แสดงเฉพาะผู้เขียนที่เป็นคน; ทำครั้งเดียวเพื่อไม่ rewrite ซ้ำหลาย branch

## สิ่งที่ยังค้าง / ทบทวนเมื่อ
ลบ backup tags หลัง PD-7

## ไฟล์/อาร์ติแฟกต์ที่เกี่ยว
`CLAUDE.md`
