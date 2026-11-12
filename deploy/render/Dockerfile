# Demo publicada de YakuTraza en un solo contenedor (Render u otro servicio similar).
#
# Los CSV de la muestra NO están en el repositorio (es público): entran por un contexto aparte, «datos»,
# que apunta a la carpeta local de los CSV. Solo se copian los ds*.csv: nunca la parte privada de los
# casos reales. La imagen resultante contiene la muestra, así que se publica en un registro PRIVADO.
#
#   docker build -f deploy/render/Dockerfile --build-context datos=C:\yakutraza\data -t yakutraza-demo .
#
# Ver deploy/render/README.md.

FROM node:20-alpine AS web
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/tsconfig.json frontend/vite.config.ts frontend/index.html ./
COPY frontend/src ./src
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    DATA_DIR=/data RULES_DIR=/rules CASOS_REALES_DIR=/casos_reales REPORTES_DIR=/srv/reportes \
    DATABASE_URL=sqlite:////srv/yakutraza.db WEB_DIR=/web \
    CASOS_REALES_PRIVADOS=false MODO_DEMO=true FECHA_CORTE=2026-09-30 TZ=America/Lima

COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir .
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY rules /rules
COPY casos_reales /casos_reales
COPY --from=datos ds*.csv /data/
COPY --from=web /app/dist /web

# La base (SQLite) se carga al construir: el servicio arranca rápido y siempre con el mismo estado inicial.
# Lo que se registre en la demo se pierde al reiniciar el servicio (Render reinicia la instancia gratuita).
RUN mkdir -p /srv/reportes && python -m app.cli seed

EXPOSE 10000
CMD ["sh", "-c", "uvicorn app.publicar:app --host 0.0.0.0 --port ${PORT:-10000}"]
