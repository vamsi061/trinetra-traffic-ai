FROM python:3.11-slim

WORKDIR /app

# System deps for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (smaller image), then other deps
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Build frontend
RUN cd frontend && npm install --quiet 2>/dev/null && npm run build 2>/dev/null

# Data dir for persistent storage
RUN mkdir -p /data && chmod -R 777 /data

ENV DATA_DIR=/data
ENV PYTHONUNBUFFERED=1

EXPOSE 7860

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
