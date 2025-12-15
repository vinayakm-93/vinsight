# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the file from your host to your current location.
COPY requirements.txt .

# Install CPU-only torch to save space (must be before requirements.txt)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Run uvicorn server
# Cloud Run expects the app to listen on PORT environment variable (default 8080)
# Run gunicorn server (Production)
# Workers: 1 per core is a good start, but for Cloud Run with 1 vCPU, 1-2 workers is standard.
# Timeout: 0 to disable timeouts (Cloud Run handles this)
CMD ["gunicorn", "main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8080", "--timeout", "0"]
