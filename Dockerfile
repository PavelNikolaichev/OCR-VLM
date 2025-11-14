FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code - separated for better caching
COPY config.py logger.py exceptions.py ./
COPY utils/ ./utils/
COPY services/ ./services/
COPY api.py main.py run.py ./

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Create .env file from example if it doesn't exist
COPY .env.example .env

# Expose ports for Streamlit and API - the 8000 is probably wouldn't needed
EXPOSE 8501 8000

# Health check for both services
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health && \
        curl --fail http://localhost:8000/health || exit 1

# Run both services
ENTRYPOINT ["/app/start.sh"]

