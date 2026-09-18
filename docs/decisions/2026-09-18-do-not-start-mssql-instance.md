# MSSQL ต่อไม่ได้ระหว่าง G6 — ไม่ start local instance เอง

- **วันที่:** 2026-09-18
- **อ้างอิง:** G6 · PD-9
- **ผู้ตัดสิน:** Project owner (ร่วมกับทีมเสมือน)

## การตัดสินใจ
ไม่ start service/container ใดๆ แม้เจอวิธี; บันทึกเป็น PD-9 รอเจ้าของ infra

## เหตุผล
ถ้าเป็น DB จริงที่หายไปโดยไม่ตั้งใจ การ "แก้ให้" อาจทับสภาพที่ทีมอื่นตั้งใจปล่อยไว้

## สิ่งที่ยังค้าง / ทบทวนเมื่อ
เมื่อ PD-9 ตอบ → reverse-engineer schema เป็น `migrations/research/mssql/001_*.sql`

## ไฟล์/อาร์ติแฟกต์ที่เกี่ยว
`docs/pending-decisions.md` PD-9
