FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Bake the spaCy model into the image so inference is fully offline
# Image size impact: ~+15 MB for en_core_web_sm
RUN python -m spacy download en_core_web_sm
# Bake the faster-whisper "base" model into the image (HF cache) so Speaking
# transcription runs fully offline at runtime. Image size impact: ~+145 MB.
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
# No surprise network at runtime: the baked model is served from the local cache.
ENV HF_HUB_OFFLINE=1
COPY . .
EXPOSE 5050
# --timeout 120: live LLM scoring (strong model + long rubric) can exceed gunicorn's 30s default
CMD ["sh", "-c", "alembic upgrade head && gunicorn -b 0.0.0.0:5050 --timeout 120 --workers 2 wsgi:app"]
