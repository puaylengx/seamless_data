CREATE TABLE `muic-data-prod.Research.publications`
(
  -- 🔹 ข้อมูลพื้นฐาน
  rank STRING NOT NULL OPTIONS (description="ลำดับผลงานในปีนั้น"),
  group_rank STRING OPTIONS (description="กลุ่มของลำดับผลงาน"),
  description STRING OPTIONS (description="รายละเอียดผลงาน"),
  product_code STRING NOT NULL OPTIONS (description="รหัสผลงาน (unique ภายในระบบ)"),
  firstname STRING NOT NULL OPTIONS (description="ชื่อผู้เขียนคนแรก"),
  lastname STRING NOT NULL OPTIONS (description="นามสกุลผู้เขียนคนแรก"),
  title STRING NOT NULL OPTIONS (description="ชื่อเรื่องของผลงาน"),
  source STRING OPTIONS (description="แหล่งที่มาของผลงาน เช่น วารสารหรือสำนักพิมพ์"),
  national_international STRING OPTIONS (description="ระดับผลงาน: national หรือ international"),
  field STRING OPTIONS (description="สาขาวิชาหรือกลุ่มสาขาของผลงาน"),
  division STRING OPTIONS (description="หน่วยงาน / ภาควิชา / สำนักวิชา ที่สังกัดของผู้เขียน"),  -- ✅ เพิ่มใหม่

  -- 🔹 วันที่และปีที่เผยแพร่
  effective_date DATE OPTIONS (description="วันที่มีผลหรือวันที่เผยแพร่จริง"),
  publication_month INT64 OPTIONS (description="เดือนที่เผยแพร่ (1–12)"),
  publication_year INT64 OPTIONS (description="ปีที่เผยแพร่ (ค.ศ.)"),
  publication_calendar_year INT64 OPTIONS (description="ปีปฏิทินของผลงาน"),
  publication_budget_year INT64 OPTIONS (description="ปีงบประมาณของผลงาน"),

  -- 🔹 กลุ่มฐานข้อมูลนานาชาติ (WoS / Scopus)
  wos_with_jif_p90 INT64 OPTIONS (description="WoS with JIF ≥ P90"),
  wos_with_jif INT64 OPTIONS (description="WoS with JIF"),
  wos_sc INT64 OPTIONS (description="WoS Science Citation Index"),
  wos_ss INT64 OPTIONS (description="WoS Social Science Citation Index"),
  wos_ah INT64 OPTIONS (description="WoS Arts & Humanities Citation Index"),
  wos_es INT64 OPTIONS (description="WoS Emerging Sources Citation Index"),

  scopus_sjr_10 INT64 OPTIONS (description="Scopus SJR Top 10%"),
  scopus_q1 INT64 OPTIONS (description="Scopus Quartile 1"),
  scopus_q2 INT64 OPTIONS (description="Scopus Quartile 2"),
  scopus_q3 INT64 OPTIONS (description="Scopus Quartile 3"),
  scopus_q4 INT64 OPTIONS (description="Scopus Quartile 4"),
  scopus_no_q INT64 OPTIONS (description="Scopus ไม่มี Quartile"),

  -- 🔹 ฐานข้อมูลอื่น ๆ
  sense_abc INT64 OPTIONS (description="ฐานข้อมูล SENSE A B C"),
  eric INT64 OPTIONS (description="ฐานข้อมูล ERIC"),
  math_sci_net INT64 OPTIONS (description="ฐานข้อมูล MathSciNet"),
  pubmed INT64 OPTIONS (description="ฐานข้อมูล PubMed"),
  jstor INT64 OPTIONS (description="ฐานข้อมูล JSTOR"),
  project_muse INT64 OPTIONS (description="ฐานข้อมูล Project Muse"),
  other_inter INT64 OPTIONS (description="ฐานข้อมูลนานาชาติอื่น ๆ"),

  -- 🔹 ฐานข้อมูลภายในประเทศ
  tci_group1 INT64 OPTIONS (description="TCI กลุ่ม 1"),
  tci_group2 INT64 OPTIONS (description="TCI กลุ่ม 2"),
  national_journal INT64 OPTIONS (description="วารสารภายในประเทศ (ไม่อยู่ใน TCI)"),

  -- 🔹 SDG Goals (1–17)
  sdg1 INT64 OPTIONS (description="SDG 1: No Poverty"),
  sdg2 INT64 OPTIONS (description="SDG 2: Zero Hunger"),
  sdg3 INT64 OPTIONS (description="SDG 3: Good Health and Well-being"),
  sdg4 INT64 OPTIONS (description="SDG 4: Quality Education"),
  sdg5 INT64 OPTIONS (description="SDG 5: Gender Equality"),
  sdg6 INT64 OPTIONS (description="SDG 6: Clean Water and Sanitation"),
  sdg7 INT64 OPTIONS (description="SDG 7: Affordable and Clean Energy"),
  sdg8 INT64 OPTIONS (description="SDG 8: Decent Work and Economic Growth"),
  sdg9 INT64 OPTIONS (description="SDG 9: Industry, Innovation, and Infrastructure"),
  sdg10 INT64 OPTIONS (description="SDG 10: Reduced Inequalities"),
  sdg11 INT64 OPTIONS (description="SDG 11: Sustainable Cities and Communities"),
  sdg12 INT64 OPTIONS (description="SDG 12: Responsible Consumption and Production"),
  sdg13 INT64 OPTIONS (description="SDG 13: Climate Action"),
  sdg14 INT64 OPTIONS (description="SDG 14: Life Below Water"),
  sdg15 INT64 OPTIONS (description="SDG 15: Life on Land"),
  sdg16 INT64 OPTIONS (description="SDG 16: Peace, Justice and Strong Institutions"),
  sdg17 INT64 OPTIONS (description="SDG 17: Partnerships for the Goals")
)
-- ✅ ถ้าต้องการ partition จริง (สามารถเปิดใช้ได้ภายหลัง)
-- PARTITION BY RANGE_BUCKET (publication_year, GENERATE_ARRAY(2000, 2035, 1))
CLUSTER BY product_code, firstname, lastname, title
OPTIONS
(
  description = "ตารางเก็บข้อมูลผลงานวิจัยและสิ่งพิมพ์ (Publication) สำหรับงานวิจัยของ MUIC",
  labels = [("env","prod"),("team","data"),("domain","research")]
);