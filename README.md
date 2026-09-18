# seamless_data

Data pipeline (Finance / Research / Zeal Data) → PostgreSQL / MSSQL / BigQuery → dashboard

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env            # กรอกค่าให้ครบ — ขาดตัวไหน pipeline จะบอกชื่อ env var ตอนรัน (ไม่มี default เป็นที่อยู่ infra)
.venv/bin/pre-commit install     # gitleaks + ruff ก่อน commit (macOS: ดู SSL_CERT_FILE ด้านล่าง)
.venv/bin/python -m pytest tests -q          # unit tests (ไม่ต่อ DB)
python migrations/migrate.py --status        # ดู migration ที่ apply แล้ว (PostgreSQL)
```

## Module map

| path | หน้าที่ | รันอย่างไร |
|---|---|---|
| `src/finance/` | ERP 2025 (Excel → PostgreSQL `erp_2025`): `extractor` → `transformer` → `validator` (+ referential/timeliness/fiscal cross-check) → `loader` | `python src/finance/main.py [append\|replace]` |
| `src/finance/master/` | master tables 9 ตาราง + `MasterValidator` (key ว่าง/ซ้ำ → fail) | `python src/finance/master/main.py [table\|all] [replace\|append]` (replace ต้อง `ALLOW_REPLACE=true`) |
| `src/finance/reference.py` | reference sets จากไฟล์ master สำหรับ consistency check | ใช้โดย finance main |
| `src/research/publication/` | ผลงานตีพิมพ์: raw → draft template (review) → MSSQL + BigQuery (MERGE) + reconcile | `python src/research/publication/main.py <template\|pipeline\|export\|upload\|upload_bq> <xlsx>` |
| `src/research/track_evaluation/` | ประเมินผลงาน: เหมือน publication; `coerce_and_clean` เป็นจุดเดียวของ transformation | `python src/research/track_evaluation/main.py <...>` |
| `src/research/reconcile.py` | เทียบ batch ที่เขียน vs ปลายทาง และ MSSQL ⇄ BigQuery ต่อปี (WARNING ไม่ raise) | เรียกอัตโนมัติหลัง upload |
| `helpers/connect_db/` | `config.py` (ตรวจ env ครบก่อนต่อ), `connection.py` (PostgreSQL ssh/direct), `mssql.py`, `bigquery.py`, `urls.py` (`URL.create`) | — |
| `helpers/replace_guard.py`, `helpers/fiscal.py`, `helpers/logger.py` | ALLOW_REPLACE guard · นิยามปีงบ (เริ่ม ต.ค.) · logger กลาง (`src` + main) | — |
| `migrations/` | `finance/` (PostgreSQL, `migrate.py` + `schema_migrations`), `research/bigquery/`, `research/mssql/` | ดู `migrations/README.md` |
| `tests/` | unit tests ทั้งหมด synthetic data ไม่ต่อ DB; `test_connection.py` = integration (`-m integration`) | CI ทุก PR |
| `docs/` | `gap-tracker.md` (สถานะ G1–G22), `pending-decisions.md` (รอนอกทีม), `decisions/` (ตัดสินแล้ว), `db-roles.md`, `finance-questions-*.md` | — |

**Logs:** `logs/<domain>/*.log` — ทุก run ปิดท้ายด้วยบรรทัด `JOB SUMMARY job=… status=… duration=… rows_in=… rows_out=…` (grep ได้สำหรับ monitoring); upload flag ทุกตัว default `false`

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

## Setup / environment (Phase 2 · G14)

- dependency ทุกตัว **pin เวอร์ชันแน่นอน** ใน `requirements.txt` / `requirements-dev.txt` — เปลี่ยนเวอร์ชันต้องเป็น PR แยก + pytest + docker build ผ่าน
- system deps ที่ pip ให้ไม่ได้: `mdb-tools` (zeal_data), `unixODBC` + **ODBC Driver 18 for SQL Server** (research MSSQL) — `Dockerfile` ติดตั้งครบ; บน macOS: `brew install mdbtools unixodbc` + Microsoft `msodbcsql18`
- `Dockerfile` เป็น multi-stage: **`runtime`** (default — ไม่มี pytest/ruff/`tests/`) และ **`test`** (`--target test` = runtime + `requirements-dev.txt` + `tests/`, CMD = pytest) · CI build ทั้งสอง target ทุก PR (build เท่านั้น ไม่ run) · image ไม่มี credential — mount `.env` และ key ตอน run (`.dockerignore` กัน `.env`, `*.json`, `data/`, `logs/`)
