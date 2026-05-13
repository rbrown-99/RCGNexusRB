FROM python:3.12-slim

WORKDIR /app

# system deps for ortools
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Build context is the repo root ("Albertsons Trucking Demo/").
# Build with: docker build -f backend/Dockerfile -t albrouting-backend .
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/src/ ./src/
COPY sample_data/ /sample_data/

ENV SAMPLE_DATA_DIR=/sample_data
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
