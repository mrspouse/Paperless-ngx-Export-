# Lightweight Python base image
FROM python:3.13-slim

# Working directory in container
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and static assets
COPY app.py .
COPY static ./static

# Create data directory
RUN mkdir -p /data

# Expose port 5001
EXPOSE 5001

# Security: do not run as root
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app /data
USER appuser

# Start application
CMD ["python", "app.py"]

