FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Install Python dependencies
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/app/data/domain_checker.db \
    LOG_FILE=/app/logs/domain_checker.log

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD python3 -c "import sys, sqlite3; conn = sqlite3.connect('${DATABASE_PATH:-/app/data/domain_checker.db}'); conn.execute('SELECT 1'); conn.close(); sys.exit(0)" || exit 1

# Volumes
VOLUME ["/app/data", "/app/logs"]

CMD ["python", "-m", "domain_checker"]
