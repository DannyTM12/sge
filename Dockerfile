FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para asyncpg y bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar solo el archivo de dependencias primero (cache layer)
COPY pyproject.toml .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        fastapi>=0.111.0 \
        "uvicorn[standard]>=0.30.0" \
        sqlalchemy>=2.0.30 \
        asyncpg>=0.29.0 \
        alembic>=1.13.0 \
        pydantic>=2.7.0 \
        pydantic-settings>=2.3.0 \
        "python-jose[cryptography]>=3.3.0" \
        "passlib[bcrypt]>=1.7.4" \
        redis>=5.0.4 \
        python-multipart>=0.0.9 \
        httpx>=0.27.0

# El código fuente se monta como volumen en desarrollo (no COPY aquí)
# En producción, descomentar las siguientes líneas:
# COPY app/ ./app/
# COPY alembic/ ./alembic/
# COPY alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
