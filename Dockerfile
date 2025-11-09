# Use Python 3.11 as base image
FROM python:3.11-slim

# Install git and procps (for pgrep)
RUN apt-get update && apt-get install -y \
    git \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Fix git ownership issue for container
RUN git config --global --add safe.directory /app || true

# Expose the port (Flask default is 5000)
EXPOSE 5000

# Run the application
CMD ["python", "webhook_listener.py"]
