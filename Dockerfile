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

# Copy all static files for the frontend
# Copy HTML files (both .html and .Html extensions)
COPY . /tmp/build/
RUN find /tmp/build -maxdepth 1 -type f \( -iname "*.html" -o -iname "*.css" -o -iname "*.js" -o -iname "*.json" -o -iname "*.svg" -o -iname "*.ico" \) -exec cp {} /app/ \; && \
    if [ -d /tmp/build/icons ]; then cp -r /tmp/build/icons /app/; fi && \
    rm -rf /tmp/build

# Create /data directory for volume mount
RUN mkdir -p /data

ENV PYTHONUNBUFFERED=1

# Fly expects the app to listen on port 8080
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
