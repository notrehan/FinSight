FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput && useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-3} --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile - --error-logfile -"]
