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

## Secrets (Phase 1 · G16)

- credential ทุกชนิด (`.env`, service account JSON, SSH key) **อยู่นอก repo tree เท่านั้น** — `~/.config/seamless_data/` แล้วชี้ด้วย absolute path ใน `.env`
- pre-commit hook (`gitleaks`, `detect-private-key`, `ruff`) บล็อกก่อน commit: `pip install -r requirements-dev.txt && pre-commit install`
  - macOS + Python จาก python.org (3.12+) อาจไม่มี CA bundle → `pre-commit install`/รันครั้งแรกจะ `CERTIFICATE_VERIFY_FAILED` ตอนดาวน์โหลด hook env
    แก้ด้วย `export SSL_CERT_FILE=$(.venv/bin/python -m certifi)` ก่อนรัน (ครั้งเดียว hook env จะถูก cache) — ปัญหาเครื่อง local ไม่กระทบ CI
- CI สแกนทั้ง history ของทุก PR ด้วย gitleaks — ถ้าเจอ secret ให้หยุดและแจ้ง Security Engineer ทันที ห้าม commit ทับ
- connection string ประกอบด้วย `helpers/connect_db/urls.py` (`sqlalchemy.URL.create`) ไม่ใช้ f-string → password ไม่โผล่ใน log/traceback
