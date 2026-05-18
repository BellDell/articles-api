# Minimal Dockerfile for the Flask API
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY app /app/app

EXPOSE 5000

# Run the Flask app
CMD ["python", "-m", "app.app"]
