# migrations/ — schema เป็น source of truth (G6)

| path | ปลายทาง | รันด้วย | tracking |
|---|---|---|---|
| `finance/NNN_*.sql` | PostgreSQL `ic_finance` | `python migrations/migrate.py [finance] [--dry-run\|--status]` | ตาราง `schema_migrations` (อัตโนมัติ) |
| `research/bigquery/NNN_*.sql` | BigQuery `muic-data-prod.Research` | `bq query --use_legacy_sql=false < file` หรือ console | ยังไม่มี — บันทึกใน decision log / PR |
| `research/mssql/NNN_*.sql` | MSSQL research DB | SSMS / `sqlcmd -i file` | ยังไม่มี — บันทึกใน decision log / PR |

กติกา (team-project-instructions ข้อ 5, Data Architect):
- schema เปลี่ยน = **ไฟล์ใหม่** เลขถัดไปเสมอ ห้ามแก้ไฟล์ที่ apply แล้ว (`migrate.py` ตรวจ checksum ให้สำหรับ PG)
- `migrate.py` รันเฉพาะ `PG_SECTIONS` — research/* ไม่ถูกรันโดยสคริปต์นี้แม้สั่ง `all`
- ก่อน apply กับ production: `--dry-run` บน staging ผ่านก่อน (pre-deployment checklist, DevOps)
- `research/mssql/001_*` เป็น **snapshot ที่ reverse-engineer จากตารางจริง** (ไม่ได้ apply ที่ไหน) — ใช้เป็นจุดตั้งต้นของ audit trail; ไฟล์ถัดไปคือการเปลี่ยนแปลงจริง

หมายเหตุ BigQuery: `002_*` เป็น view นิยาม dedupe (`ROW_NUMBER() ... rn = 1` ต่อ `product_code`) ซึ่งเป็น business rule — ต้องมีใน Metric Dictionary (G12) ด้วย
