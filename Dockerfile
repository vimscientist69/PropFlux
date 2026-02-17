# Use Ubuntu 24.04 LTS as base image
FROM ubuntu:24.04

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for python3 to python
RUN ln -s /usr/bin/python3.12 /usr/bin/python

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Install Playwright browsers (if needed for JavaScript rendering)
RUN playwright install chromium && \
    playwright install-deps chromium

# Copy project files
COPY . .

# Set proper permissions
RUN chmod +x runner.py

# Default command - can be overridden
ENTRYPOINT ["python", "runner.py"]
CMD ["--site", "property24", "--verbose"]
