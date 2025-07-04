FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy test requirements and install Python dependencies
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt

# Copy application code
COPY . .

# Set environment variables for testing
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV USE_MOCK_CLIENTS=true
ENV REQUIRE_AUTHENTICATION=0

# Expose port
EXPOSE 8000

# Default command for testing
CMD ["python", "-m", "pytest", "tests/", "-v"] 