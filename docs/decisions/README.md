# Decision log — การตัดสินใจภายในทีมที่ไม่ต้องรอนอกทีม (G18)

> หนึ่งไฟล์ต่อหนึ่งการตัดสินใจ `YYYY-MM-DD-<slug>.md` · schema/metric เปลี่ยนต้องมี entry ผูกกับ migration/PR (กติกาข้อ 5)
> เรื่องที่รอคนนอกทีมอยู่ใน [`../pending-decisions.md`](../pending-decisions.md) — เมื่อได้คำตอบให้ย้ายมาที่นี่

| วันที่ | เรื่อง | อ้างอิง |
|---|---|---|
| 2026-09-17 | [MasterLoader default mode=replace ต้อง opt-in ALLOW_REPLACE](2026-09-17-master-replace-requires-allow-replace.md) | G2 · PR #1 |
| 2026-09-17 | [rewrite git history ลบ trailer Co-Authored-By: Claude](2026-09-17-rewrite-history-remove-ai-trailer.md) | PR #3, #4 |
| 2026-09-17 | [guard ALLOW_REPLACE รวมเป็น helper เดียว](2026-09-17-shared-replace-guard-helper.md) | G2 · PR #1/#2 |
| 2026-09-17 | [non-numeric score/weight ใน track_evaluation → NULL + WARNING (ไม่ fail)](2026-09-17-track-evaluation-nonnumeric-warning.md) | G3 · PR #1 |
| 2026-09-17 | [zeal_data half ของ G2 อยู่บน branch ตระกูล zeal](2026-09-17-zeal-g2-on-zeal-branch.md) | PR #2 |
| 2026-09-18 | [check ใหม่ (fiscal cross-check, referential, timeliness) เป็น WARNING ก่อน ไม่ fail-fast](2026-09-18-advisory-checks-before-fail-fast.md) | G13/G15 · PR #15, #18 |
| 2026-09-18 | [MSSQL ต่อไม่ได้ระหว่าง G6 — ไม่ start local instance เอง](2026-09-18-do-not-start-mssql-instance.md) | G6 · PD-9 |
| 2026-09-18 | [migration 003 = ADD PRIMARY KEY อย่างเดียว; การลบแถวซ้ำแยกเป็น 004 (manual)](2026-09-18-master-pk-detect-not-repair.md) | G5 · PR #17 |
| 2026-09-18 | [reconcile ตรวจแถวซ้ำจาก rows > distinct ของปลายทาง ไม่ใช่จากขนาด batch](2026-09-18-reconcile-duplicates-from-destination.md) | G4 · PR #9 |
| 2026-09-18 | [prepare_for_load คง typed dtypes; object/None เฉพาะ MSSQL path](2026-09-18-typed-dtypes-in-shared-prepare.md) | G4 · PR #9 |
