# Base image for Python backend
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY server/requirements.txt ./

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all server files
COPY server/ .

# Expose backend port
EXPOSE 8000

# Run the FastAPI server using Uvicorn
CMD ["uvicorn", "examples.app:app", "--host", "0.0.0.0", "--port", "8000"]