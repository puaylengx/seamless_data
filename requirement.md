# seamless data insert and update data to db

สร้าง project สำหรับ insert และ update

- ดำเนินการด้านข้อมูลของหลาย unit เช่น finance หรือ research
- มีการเชื่อมต่อฐานข้อมูลแบบ ssh หรือ แบบ direct ซึ่งใช้ postgresql
- ฐานข้อมูลคือ `ic_finance`

## finance

import จากไฟล์ excel

### ตาราง erp_2025

- ด้านล่างนี้คือ ตัวอย่างข้อมูล

```csv
Year,Trimester,Day,Month,DocNo,DocDate,FundsCtr,CostCtr_ID,Cost_Owner,IO_Goods,IO_Work,IO_Activity,IO_Project,Order_Description,HROT,GL_ID,GL_Description, Amount ,Details,MU_Strategy,IC_Strategy
2025,1,3,12,3000028712,03.12.2024,3001,C3001000,,,Z30000000000,,,ไม่มีโครงการ,,5302050010,ค่าเบี้ยประกัน, 1,108.00 ,คชจ.ประชุมความร่วมมือ Ireland-ค่าประกัน,,
```

จากตัวอย่าง ต้องการให้สร้างไฟล์สำหรับ migrate และ insert ข้อมูลเข้าฐานข้อมูล

CREATE TABLE IF NOT EXISTS erp_2025 (
  fiscal_year       bigint NOT NULL,
  fiscal_month      bigint NOT NULL,
  trimester         bigint NOT NULL,
  day               bigint NOT NULL,
  month             bigint NOT NULL,
  year              bigint NOT NULL,
  doc_no            bigint NOT NULL,
  doc_date          text NOT NULL,
  funds_ctr         bigint NOT NULL,
  cost_ctr_id       text NOT NULL,
  cost_owner        text,
  cost_note         numeric,
  io_goods          text,
  io_work           text,
  io_activity       text,
  io_project        text,
  order_description text,
  hr_ot             text,
  gl_id             bigint NOT NULL,
  gl_description    text NOT NULL,
  amount            numeric NOT NULL,
  details           text NOT NULL,
  mu_strategy       numeric,
  ic_strategy       numeric,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ,
  updated_by        TEXT,
  created_by        TEXT
);

### ตาราง master

- ชื่อตาราง master
  - master_cost_ctr
    - เปลี่ยนชื่อ column
      - CostCtr_Id เป็น cost_center_id
      - CostCtr_Description เป็น cost_center_description
      - CostCtr_Eng เป็น cost_center_eng
      - CostCtr_TH เป็น cost_center_th
    - เพิ่ม column
      - status
      - created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      - updated_at  TIMESTAMPTZ,
      - updated_by  TEXT,
      - created_by  TEXT
  - master_fund
    - เปลี่ยนชื่อ column
      - Fund_Id เป็น fund_id
      - Fund_Description เป็น fund_description
    - เพิ่ม column
      - status
      - created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      - updated_at  TIMESTAMPTZ,
      - updated_by  TEXT,
      - created_by  TEXT
  - master_gl
    - เปลี่ยนชื่อ column
      - Group เป็น group_id
      - Id เป็น gl_id
      - Description เป็น gl_description
      - Group_Description เป็น group_description
    - เพิ่ม column
      - status
      - created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      - updated_at  TIMESTAMPTZ,
      - updated_by  TEXT,
      - created_by  TEXT
  - master_io_goods
    - เปลี่ยนชื่อ column
      - IO_Goods_Id เป็น io_good_id
      - IO_Goods_Description เป็น io_good_description
    - เพิ่ม column
      - status
      - created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      - updated_at  TIMESTAMPTZ,
      - updated_by  TEXT,
      - created_by  TEXT
  - master_io_activities
    - เปลี่ยนชื่อ column
      - IO_Activity_Id เป็น io_activity_id
      - IO_Activity_Description เป็น io_activity_description
    - เพิ่ม column
      - status
      - created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      - updated_at  TIMESTAMPTZ,
      - updated_by  TEXT,
      - created_by  TEXT
  - master_io_project
    - เปลี่ยนชื่อ column
      - IO_Project เป็น io_project_id
      - IO_Project_Description เป็น io_project_description
      - CostCtr เป็น cost_center_id
      - ID_ICST เป็น ic_strategy_id
      - ID_MUST เป็น mu_strategy_id
    - เพิ่ม column
      - status
      - created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      - updated_at  TIMESTAMPTZ,
      - updated_by  TEXT,
      - created_by  TEXT
  - master_io_work
    - เปลี่ยนชื่อ column
      - IO_Work_Id เป็น io_work_id
      - IO_Work_Description เป็น io_work_description
      - status
    - เพิ่ม column
      - created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      - updated_at  TIMESTAMPTZ,
      - updated_by  TEXT,
      - created_by  TEXT
  - master_ic_strategy
    - เปลี่ยนชื่อ column
      - ID_ICST เป็น ic_strategy_id
      - Year_start เป็น start_year
      - Year_end เป็น end_year
      - Name เป็น name_en
      - Description เป็น ic_strategy_description
      - status
    - เพิ่ม column
      - created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      - updated_at  TIMESTAMPTZ,
      - updated_by  TEXT,
      - created_by  TEXT
  - master_mu_strategy
    - เปลี่ยนชื่อ column
      - ID_MUST เป็น mu_strategy_id
      - Year_start เป็น start_year
      - Year_end เป็น end_year
      - Name เป็น name_en
      - Description เป็น mu_strategy_description
      - status
    - เพิ่ม column
      - created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      - updated_at  TIMESTAMPTZ,
      - updated_by  TEXT,
      - created_by  TEXT
