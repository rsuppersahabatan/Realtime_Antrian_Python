# Base image for Python backend
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy Pipfile and Pipfile.lock first for caching
COPY server/Pipfile server/Pipfile.lock ./

# Install dependencies
RUN pipenv install --system --deploy

# Copy all server files
COPY server/ .

# Expose backend port
EXPOSE 8000

# Run the FastAPI server using Uvicorn
CMD ["uvicorn", "examples.app:app", "--host", "0.0.0.0", "--port", "8000"]