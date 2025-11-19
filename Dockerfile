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

# Copy all HTML, CSS, JS, and static files for the frontend
# Use individual COPY commands to handle case-sensitive files
COPY *.html /app/ 2>/dev/null || true
COPY *.Html /app/ 2>/dev/null || true
COPY *.css /app/
COPY *.js /app/
COPY *.json /app/
COPY *.svg /app/ 2>/dev/null || true
COPY *.ico /app/ 2>/dev/null || true
COPY icons /app/icons 2>/dev/null || true

# Create /data directory for volume mount
RUN mkdir -p /data

ENV PYTHONUNBUFFERED=1

# Fly expects the app to listen on port 8080
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
