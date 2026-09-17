"""
Guard สำหรับ destructive replace mode ของทุก loader (DELETE ทั้งตาราง / DROP+CREATE ตารางปลายทาง)

ใช้ env var ตัวเดียวทั้งโปรเจกต์: ALLOW_REPLACE (default "false")
เปิดได้ด้วยค่า "true" เท่านั้น (ไม่สนตัวพิมพ์เล็ก-ใหญ่) — "1", "yes" ไม่นับ

ทุก loader ต้องเรียก ensure_replace_allowed() **ก่อน** เปิด connection / SSH tunnel
เพื่อให้ run ที่ถูกบล็อกไม่แตะ DB เลย
"""
import os

ENV_VAR = "ALLOW_REPLACE"


def _is_enabled() -> bool:
    return os.getenv(ENV_VAR, "false").strip().lower() == "true"


def ensure_replace_allowed(context: str) -> None:
    """
    raise RuntimeError ถ้ายังไม่ได้ opt-in ให้ทำ replace

    Args:
        context: บอกว่าจะลบอะไร เพื่อให้ข้อความ error ชี้ชัด
                 เช่น 'DELETE FROM "public"."erp_2025"' หรือ 'DROP+CREATE zeal.public.*'
    """
    if _is_enabled():
        return
    raise RuntimeError(
        f"replace mode ถูกบล็อก: {context}\n"
        f"ต้องตั้ง {ENV_VAR}=true ใน .env ก่อน (ตอนนี้เป็น "
        f"'{os.getenv(ENV_VAR, '<ไม่ได้ตั้ง>')}')\n"
        "ถ้าตั้งใจล้างข้อมูลจริง ให้ตั้ง true ชั่วคราว แล้วรีเซ็ตกลับเป็น false "
        "ทันทีหลังรันเสร็จ (pre-deployment checklist)"
    )
