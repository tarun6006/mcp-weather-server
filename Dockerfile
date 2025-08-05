# Use Python 3.13.5 slim image based on Debian Bookworm
# Includes security fixes for CVE-2024-12718 (tarfile path traversal vulnerability)
FROM python:3.13.5-slim-bookworm

# Set working directory
WORKDIR /app

# Create non-root user for enhanced security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Update system packages and clean up package cache to reduce image size
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies with no cache to reduce image size
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Set ownership of application files to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user for security
USER appuser

# Expose port 8080 for Google Cloud deployment
EXPOSE 8080

# Configure environment variables for Flask application
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
# Set PORT to 8080 for Google Cloud deployment
ENV PORT=8080

# Start the Flask application
CMD ["python", "app.py"]
