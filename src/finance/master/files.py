"""
mapping master table → ชื่อไฟล์ Excel ใน data/finance/clean/master/ (ไม่มี side effect ตอน import)

แยกออกจาก master/main.py เพราะ finance/main.py และ reference.py ต้องใช้ mapping นี้ — ถ้า import main.py
จะไปสร้าง logger ของ master ระหว่าง run ของ ERP แล้วแย่ง handler ของ "src" logger (G18)
เมื่อได้ไฟล์ master รุ่นใหม่จาก Finance (PD-13) แก้ชื่อไฟล์ที่นี่ที่เดียว
"""

MASTER_FILES: dict[str, str] = {
    "master_cost_ctr":      "Master_CostCtr_20240605.xlsx",
    "master_fund":          "Master_FUND_20221118.xlsx",
    "master_gl":            "Master_GL_20230531.xlsx",
    "master_io_goods":      "Master_IO_Goods_20230531.xlsx",
    "master_io_activities": "Master_IO_Activity_20230531.xlsx",
    "master_io_project":    "Master_IO_Project_20230531.xlsx",
    "master_io_work":       "Master_IO_Work_20230531.xlsx",
    "master_ic_strategy":   "Master_IC_Strategy_20230531.xlsx",
    "master_mu_strategy":   "Master_MU_Strategy_20230531.xlsx",
}
