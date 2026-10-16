FROM node:24.12.0-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
FROM python:3.12.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY backend ./backend
COPY data ./data
COPY --from=frontend /build/dist ./frontend/dist
USER 10001:10001
EXPOSE 8000
CMD ["sh", "-c", "python -m backend.seed && exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1"]
