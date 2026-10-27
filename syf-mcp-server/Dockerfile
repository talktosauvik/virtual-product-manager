FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir "mcp[cli]>=1.6.0,<2.0.0" "google-cloud-storage>=2.18.0" "starlette>=0.40.0,<1.0.0" "uvicorn>=0.32.0"

COPY . .
ENV PORT=8080
EXPOSE 8080
CMD ["python", "server.py"]
