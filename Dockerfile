# seamless_data — images (G14)
#
#   runtime (default) : system deps + pinned runtime deps + src/helpers/migrations — ไม่มี pytest/ruff/tests
#   test              : runtime + requirements-dev + tests/  — ใช้ใน CI / dev เท่านั้น
#
#   docker build -t seamless_data .                       # runtime
#   docker build --target test -t seamless_data:test .    # test image
#   docker run --rm seamless_data:test                    # = python -m pytest tests -q
#   docker run --rm --env-file .env -v ~/.config/seamless_data:/secrets:ro \
#              -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/muic-data-prod.json \
#              seamless_data python src/finance/main.py append
#
# ไม่มี credential ใน image — .env / service-account key mount ตอน run เท่านั้น (ดู .dockerignore)

# ══════════════════════════════════════════════════════════════
# stage 1: base — system deps ที่ pip ให้ไม่ได้
# ══════════════════════════════════════════════════════════════
FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ACCEPT_EULA=Y

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

# ══════════════════════════════════════════════════════════════
# stage 2: runtime — production image (ไม่มี dev deps, ไม่มี tests)
# ══════════════════════════════════════════════════════════════
FROM base AS runtime

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY pyproject.toml README.md ./
COPY helpers ./helpers
COPY src ./src
COPY migrations ./migrations

# non-root (least privilege ระดับ container)
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

# ตรวจว่า driver/เครื่องมือครบตั้งแต่ build (fail เร็ว ไม่รอ runtime) — แยกบรรทัดกัน || กลบ error
RUN python -c "import pyodbc; d = pyodbc.drivers(); assert 'ODBC Driver 18 for SQL Server' in d, d; print('ODBC drivers:', d)"
RUN command -v mdb-tables && command -v mdb-export
RUN python -c "import pandas, numpy, sqlalchemy, google.cloud.bigquery as bq; print('pandas', pandas.__version__, 'numpy', numpy.__version__)"
RUN python -c "import pytest" 2>/dev/null && (echo 'pytest must not be in runtime image' && exit 1) || echo "runtime image: no dev deps ✓"

# ไม่มี default command ที่เขียน DB — ต้องระบุ pipeline เองตอน run
CMD ["python", "-c", "print('seamless_data runtime image — ระบุคำสั่ง pipeline เอง เช่น: python src/finance/main.py append')"]

# ══════════════════════════════════════════════════════════════
# stage 3: test — runtime + dev deps + tests (CI / dev เท่านั้น)
# ══════════════════════════════════════════════════════════════
FROM runtime AS test

USER root
COPY requirements-dev.txt ./
RUN pip install -r requirements-dev.txt
COPY tests ./tests
RUN chown -R app:app /app
USER app

CMD ["python", "-m", "pytest", "tests", "-q"]
