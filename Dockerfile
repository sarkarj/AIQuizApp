# AI Quiz Platform - Dockerfile
# Version: 1.1.0 - Optimized for macOS M1
# Fixes OSError [Errno 35] Resource deadlock avoided

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set proper permissions (important for macOS M1)
RUN chmod -R 755 /app

# Expose Streamlit port
EXPOSE 8510

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8510/_stcore/health || exit 1

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# Run Streamlit
CMD ["streamlit", "run", "app.py", \
    "--server.port=8510", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--server.fileWatcherType=none", \
    "--server.runOnSave=false", \
    "--browser.gatherUsageStats=false"]