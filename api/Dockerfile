FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Immutable data only: no NLTK library and no request-time corpus download.
COPY app/services/metric_resources.py app/services/metric_resources.py
RUN python app/services/metric_resources.py --prepare
# Keep the established syntax model and local ASR model in the full image.
RUN python -m spacy download en_core_web_sm
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
ENV HF_HUB_OFFLINE=1
COPY . .
RUN python app/services/metric_resources.py --check
EXPOSE 5050
# Production Compose uses its separate migrate service; this retains local use.
CMD ["sh", "-c", "DATABASE_URL=\"${MIGRATION_DATABASE_URL:-$DATABASE_URL}\" alembic upgrade head && exec gunicorn -b 0.0.0.0:5050 --timeout 120 --workers 2 wsgi:app"]
