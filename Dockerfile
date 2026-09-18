# seamless_data — runtime image (G14)
# มี system deps ครบสำหรับทุก pipeline: mdb-tools (zeal_data .mdb), unixODBC + ODBC Driver 18 (research MSSQL)
# ไม่มี credential ใน image — .env / service-account key mount ตอน run เท่านั้น (ดู .dockerignore)
#
#   docker build -t seamless_data .
#   docker run --rm --env-file .env -v ~/.config/seamless_data:/secrets:ro \
#              -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/muic-data-prod.json \
#              seamless_data python -m pytest tests -q
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ACCEPT_EULA=Y

# ── system deps ───────────────────────────────────────────────
# mdb-tools  : mdb-tables / mdb-export สำหรับ src/aditayathorn/zeal_data
# unixodbc   : runtime ของ pyodbc
# msodbcsql18: "ODBC Driver 18 for SQL Server" จาก Microsoft apt repo (ต้อง ACCEPT_EULA=Y)
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        curl gnupg ca-certificates \
        mdbtools \
        unixodbc; \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg; \
    echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends msodbcsql18; \
    apt-get purge -y --auto-remove curl gnupg; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── python deps (pinned) — layer แยกเพื่อ cache ─────────────────
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt -r requirements-dev.txt

# ── source ────────────────────────────────────────────────────
COPY pyproject.toml README.md ./
COPY helpers ./helpers
COPY src ./src
COPY migrations ./migrations
COPY tests ./tests

# non-root (least privilege ระดับ container)
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

# ตรวจว่า driver/เครื่องมือครบตั้งแต่ build (fail เร็ว ไม่รอ runtime) — แยกบรรทัดกัน || กลบ error
RUN python -c "import pyodbc; d = pyodbc.drivers(); assert 'ODBC Driver 18 for SQL Server' in d, d; print('ODBC drivers:', d)"
RUN command -v mdb-tables && command -v mdb-export
RUN python -c "import pandas, numpy, sqlalchemy, google.cloud.bigquery as bq; print('pandas', pandas.__version__, 'numpy', numpy.__version__)"

CMD ["python", "-m", "pytest", "tests", "-q"]
