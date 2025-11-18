# Dockerfile

FROM python:3.11-slim

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend code and optimizer
COPY backend /app/backend
COPY moonlighter_optimizer.py /app/moonlighter_optimizer.py

# Copy faculty.csv so the app can seed providers
COPY faculty.csv /app/faculty.csv

ENV PYTHONUNBUFFERED=1

# Fly expects the app to listen on port 8080
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
