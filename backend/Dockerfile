FROM python:3.11-slim

ARG SOURCE_DIR=.
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY ${SOURCE_DIR}/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY ${SOURCE_DIR}/ .

# Run as non-root user (H-08)
RUN addgroup --system app && adduser --system --ingroup app app
USER app:app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]