# First stage: build dependencies
FROM cgr.dev/chainguard/python:latest-dev AS builder

ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"

WORKDIR /app

RUN python -m venv /app/venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Second stage: production image
FROM cgr.dev/chainguard/python:latest

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH=/app
ENV FLASK_ENV=production  
ENV FLASK_DEBUG=0 

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:5000/health || exit 1

# Copy virtual environment and all application code including tests
COPY --from=builder /app/venv /venv
COPY . .

EXPOSE 5000
ENTRYPOINT ["python", "-m", "src.app"]