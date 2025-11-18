FROM python:3.9.6 AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app


RUN python -m venv .venv
COPY requirements.txt ./
RUN .venv/bin/pip install -r requirements.txt
FROM python:3.9.6-slim
WORKDIR /app
COPY --from=builder /app/.venv .venv/
COPY . .
CMD ["/app/.venv/bin/fastapi", "run"]
# Use a slim Python base image
FROM python:3.11-slim

# Prevent Python from writing .pyc and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set working directory
WORKDIR /app

# Install basic build tools (needed for some Python deps)
RUN apt-get update && apt-get install -y \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend code and optimizer into the container
COPY backend /app/backend
COPY moonlighter_optimizer.py /app/moonlighter_optimizer.py
# If you have other helper Python files that backend imports,
# add them here with more COPY lines.

# ⬇️ NEW: copy your faculty CSV into the image
COPY faculty.csv /app/faculty.csv

# Expose the port the app will listen on inside the container
EXPOSE 8000

# Start FastAPI using uvicorn on port 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
