# seamless_data

Data pipeline (Finance / Research / Zeal Data) → PostgreSQL / MSSQL / BigQuery → dashboard

- ทีมเสมือน กติกา และมาตรฐานที่ยึดถือ: [docs/team-project-instructions.md](docs/team-project-instructions.md)
- Gap analysis + roadmap: [docs/gap-analysis-2026-09.md](docs/gap-analysis-2026-09.md)
- เรื่องที่รอคำตอบจากนอกทีม: [docs/pending-decisions.md](docs/pending-decisions.md)

## Destructive replace guard (Phase 0 · G2)

`mode="replace"` ของทุก loader (DELETE ทั้งตาราง / DROP+CREATE ตารางปลายทาง) ถูกบล็อกโดย default
ต้องตั้ง `ALLOW_REPLACE=true` ใน `.env` ชั่วคราวก่อนรัน แล้วรีเซ็ตกลับเป็น `false` ทันทีหลังเสร็จ

> ⚠️ `python src/finance/master/main.py` ใช้ `replace` เป็น default อยู่แล้ว
> จึง **error ทันทีถ้าไม่ตั้ง `ALLOW_REPLACE=true`** — ตั้งใจเปลี่ยนจาก Phase 0 (G2)
> ตามกติกา security-by-default ไม่ใช่ bug

guard อยู่ที่ `helpers/replace_guard.py` ตัวเดียว ใช้ร่วมกันทั้ง finance และ zeal_data
