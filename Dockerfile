# Multi-stage: build React wallet UI, then ship with FastAPI for single-URL live host.
FROM node:22-alpine AS web-build
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY seed_api_demo.py main.py ./
COPY data ./data
COPY --from=web-build /web/dist ./web/dist
RUN mkdir -p /app/data/exports

ENV APP_ENV=production
ENV SEED_DEMO=true
# Render (and most PaaS) inject PORT — do not hardcode 8000 only
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
