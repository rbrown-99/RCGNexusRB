FROM python:3.12-slim

WORKDIR /app

# Build context is the repo root ("Albertsons Trucking Demo/").
# Build with: docker build -f mcp-server/Dockerfile -t albrouting-mcp .
COPY mcp-server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp-server/src/ ./src/

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "src.server"]
