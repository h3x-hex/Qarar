FROM python:3.12-slim

WORKDIR /app

# Install Python deps first for better layer caching.
COPY qarar/requirements.txt qarar/requirements.txt
RUN pip install --no-cache-dir -r qarar/requirements.txt

# Ship the app and the datasets it reads at runtime.
# data_layer.py resolves DATA_DIR to ../data relative to qarar/, so both
# directories must live side by side under /app.
COPY qarar/ qarar/
COPY data/ data/

# Railway injects $PORT at runtime; default to 8000 for local `docker run`.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn api:app --app-dir qarar --host 0.0.0.0 --port ${PORT:-8000}"]
