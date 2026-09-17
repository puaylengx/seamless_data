# DB Roles & Privileges — Principle of Least Privilege (G7)

> เจ้าภาพ: **Security & Compliance Engineer** · สถานะ: **ข้อเสนอ** — grant จริงบน DB ยังไม่ได้ตรวจ (รอ [PD-5](pending-decisions.md) จาก DBA)
> หลักการ: user ที่ pipeline ใช้ต้อง **ไม่มี** สิทธิ์ DDL (CREATE/ALTER/DROP/TRUNCATE) — schema เปลี่ยนได้ทางเดียวคือ migration ที่รันด้วย role แยก (กติกาข้อ 5)

## สิ่งที่โค้ดต้องการจริง (หลัง G2 + G7)

| Pipeline | ปลายทาง | คำสั่งที่รัน | สิทธิ์ขั้นต่ำ |
|---|---|---|---|
| finance ERP / master (`mode=append`) | PostgreSQL `ic_finance` | `INSERT` | `INSERT` |
| finance ERP / master (`mode=replace`, ต้อง `ALLOW_REPLACE=true`) | PostgreSQL | `DELETE FROM` ทั้งตาราง + `INSERT` ใน transaction เดียว | `DELETE`, `INSERT` (**ไม่ต้อง** `TRUNCATE` แล้ว — G7) |
| finance reconcile/validate อนาคต (G13) | PostgreSQL | `SELECT` master | `SELECT` |
| research publication / track_evaluation | MSSQL research DB | `INSERT` (`to_sql append`), `SELECT` (reconcile G4, `check_string_lengths` อ่าน `INFORMATION_SCHEMA`) | `INSERT`, `SELECT` |
| research publication / track_evaluation | BigQuery `Research` | load → staging (`WRITE_TRUNCATE` = ลบ/สร้าง staging), `MERGE` เข้า prod, `SELECT` (reconcile) | `bigquery.dataEditor` **เฉพาะ dataset** + `jobUser` ระดับ project |
| zeal_data ingest (`ZEAL_INSERT_MODE=replace`) | PostgreSQL zeal | pandas `if_exists="replace"` = `DROP TABLE` + `CREATE TABLE` + `INSERT` | ยังต้อง owner ของตาราง — **ยกเว้นที่ยอมรับชั่วคราว** (raw/bronze layer, schema มาจาก .mdb โดยตรง) ดูหมายเหตุล่าง |
| `migrations/migrate.py` | PostgreSQL | `CREATE TABLE`, อนาคต `ALTER` | DDL — **ต้องเป็น role แยก** |

## Role ที่เสนอ (PostgreSQL)

```sql
-- 1) เจ้าของ schema: รัน migration เท่านั้น ไม่ใช้ใน .env ของ pipeline
CREATE ROLE schema_owner LOGIN PASSWORD '...';
GRANT ALL ON SCHEMA public TO schema_owner;
-- ตารางที่ migration สร้างจะเป็นของ schema_owner โดยอัตโนมัติ

-- 2) pipeline writer: DML อย่างเดียว ไม่มี TRUNCATE/DDL
CREATE ROLE etl_writer LOGIN PASSWORD '...';
GRANT USAGE ON SCHEMA public TO etl_writer;
GRANT SELECT, INSERT, DELETE ON ALL TABLES IN SCHEMA public TO etl_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE schema_owner IN SCHEMA public
  GRANT SELECT, INSERT, DELETE ON TABLES TO etl_writer;   -- ตารางใหม่จาก migration ได้สิทธิ์อัตโนมัติ

-- 3) dashboard / BI: อ่านได้เฉพาะ reporting view (G8/G12) ไม่เห็น raw table
CREATE ROLE bi_reader LOGIN PASSWORD '...';
GRANT USAGE ON SCHEMA public TO bi_reader;
-- GRANT SELECT ON v_finance_erp_report TO bi_reader;  -- เมื่อ view จาก G10 มีจริง
```

ตรวจสิทธิ์ปัจจุบันของ user ใน `.env` (DBA รัน):
```sql
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = current_user;
SELECT table_name, privilege_type FROM information_schema.role_table_grants
 WHERE grantee = current_user ORDER BY 1, 2;
```
ผ่านเกณฑ์เมื่อ: `rolsuper = false` และไม่มี `TRUNCATE`, `REFERENCES`, `TRIGGER` ใน privilege_type ของ pipeline user

## MSSQL (research)

- pipeline user: `db_datareader` + `db_datawriter` บน research DB เท่านั้น — **ไม่ใช่** `db_owner`/`db_ddladmin`
- ตรวจ: `SELECT dp.name, r.name AS role FROM sys.database_role_members m JOIN sys.database_principals dp ON m.member_principal_id = dp.principal_id JOIN sys.database_principals r ON m.role_principal_id = r.principal_id;`
- schema ของ `publications` / `track_evaluation` ยังไม่มีใน repo (G6) → migration ต้องรันด้วย login แยกเช่นกัน

## BigQuery (research)

- service account ใน `GOOGLE_APPLICATION_CREDENTIALS`: `roles/bigquery.dataEditor` **บน dataset `Research`** (ไม่ใช่ระดับ project) + `roles/bigquery.jobUser` ระดับ project
- dashboard: `roles/bigquery.dataViewer` บน **authorized view** เท่านั้น ไม่ให้ตรงบน table `publications` ที่มีชื่อนักวิจัย (G8/PD-6)
- ตรวจ: `gcloud projects get-iam-policy muic-data-prod --flatten="bindings[].members" --filter="bindings.members:<sa-email>"`

## หมายเหตุ / ข้อยกเว้น

1. **zeal_data replace = DROP+CREATE** — ยังต้องสิทธิ์ owner เพราะ schema สร้างจาก .mdb ผ่าน pandas โดยไม่มี migration; guard `ALLOW_REPLACE` (G2) เป็นชั้นป้องกันเดียวตอนนี้ ทางออกระยะยาวคือใส่ zeal เข้า `migrations/` แล้วเปลี่ยนเป็น `DELETE` + `append` (G6/G11) — ระบุเป็นข้อยกเว้นที่รู้แล้ว ไม่ใช่ลืม
2. **BigQuery staging `WRITE_TRUNCATE`** — เป็น semantics ของ load job (ลบเนื้อหา staging แล้วเขียนใหม่) อยู่ใน `dataEditor` อยู่แล้ว ไม่ต้องสิทธิ์เพิ่ม
3. `migrations/migrate.py` ปัจจุบันใช้ connection เดียวกับ pipeline (`connect_to_db()`) → เมื่อแยก role แล้วต้องเพิ่ม `MIGRATION_DB_USERNAME/PASSWORD` ใน `.env.example` (ทำใน G6 พร้อม `schema_migrations`)

## Pre-deployment checklist (Security) — เพิ่มจาก G7

- [ ] pipeline user ไม่มี superuser / DDL / TRUNCATE (query ด้านบน)
- [ ] `.env` จริง: `ALLOW_REPLACE=false` (หรือไม่ตั้ง) และ upload flags เป็น `false` หลังรันเสร็จ
- [ ] service account BigQuery ผูกกับ dataset ไม่ใช่ project
- [ ] credential ไม่ expired (SSH key, SA key rotation)
