# Use official Python lightweight image
FROM python:3.9-slim

# Set working directory to the project root
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8080
ENV PYTHONPATH /app:/app/backend

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything from the local folder to the container's /app
COPY . .

# Move to the backend folder where app.py is located
WORKDIR /app/backend

# Run the application using uvicorn
# We use the list format for CMD to ensure it handles signals correctly
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
