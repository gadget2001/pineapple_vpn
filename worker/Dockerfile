FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/app /app/app

CMD ["celery", "-A", "app.celery_app.celery_app", "worker", "-l", "info"]
