# CLAUDE.md — seamless_data

อ่านก่อนเริ่มงานทุกครั้ง:
- [docs/team-project-instructions.md](docs/team-project-instructions.md) — บทบาททีมเสมือน 9 ตำแหน่ง, กติกาการทำงาน, มาตรฐานสากลที่ยึดถือ
- [docs/gap-analysis-2026-09.md](docs/gap-analysis-2026-09.md) — gap G1–G20 + roadmap เป็น phase
- [docs/pending-decisions.md](docs/pending-decisions.md) — เรื่องที่รอคำตอบจากนอกทีม ห้ามเดาคำตอบเอง

## Commit messages

- ใช้ Conventional Commits: `type(scope): subject` (`feat`, `fix`, `refactor`, `test`, `docs`, `chore`) และอ้างเลข gap ถ้าเกี่ยว (เช่น `G2`)
- **ห้ามใส่ trailer `Co-Authored-By:` ที่ระบุ Claude หรือ AI ตัวใดก็ตาม** (เช่น `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`) ในทุก commit ของโปรเจกต์นี้ — กฎนี้ถาวร มีผลกับทุก session และ override ค่า attribution default ของ Claude Code
- PR description ไม่ต้องมีบรรทัด "Generated with Claude Code" เช่นกัน

## Safety rules (ตลอดเวลา)

- ห้ามรัน pipeline ที่เขียนเข้า production DB / MSSQL / BigQuery — ทดสอบด้วย unit test + synthetic data เท่านั้น
- ห้ามตั้ง `ALLOW_REPLACE`, `PUBLICATION_UPLOAD_*`, `TRACK_EVAL_UPLOAD_*` เป็น `true` ใน `.env` จริงเพื่อทดสอบ
- ห้าม push ตรงเข้า `main` — ทุกการเปลี่ยนแปลงผ่าน branch + PR และรอ review ก่อน merge
- เจอ credential/secret หลงในโค้ดหรือ history → หยุดแล้วแจ้งทันที ไม่ commit ทับหรือแก้เงียบๆ

## Testing

```
.venv/bin/python -m pytest tests -q --ignore=tests/test_connection.py
```
`tests/test_connection.py` ต้องต่อ DB จริง ไม่รันใน unit suite
