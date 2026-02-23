# Use official Python lightweight image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8080

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ /app/backend/

# Copy data files from root to /app (so data_loader can find them relative to its location)
COPY route_stop_ordered.csv /app/
COPY route_edges.csv /app/
COPY chennai_bus_stops.csv /app/
COPY cleaned_all_stops.csv /app/

# Work from the backend directory
WORKDIR /app/backend

# Run the application
CMD uvicorn app:app --host 0.0.0.0 --port $PORT
