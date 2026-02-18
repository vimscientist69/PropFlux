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

# Create virtual environment
RUN python3 -m venv /app/.venv

# Activate virtual environment and install dependencies
RUN . /app/.venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Update PATH to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Copy project files
COPY . .

# Default command - can be overridden
ENTRYPOINT ["python", "runner.py"]
CMD ["--site", "property24", "--verbose"]
