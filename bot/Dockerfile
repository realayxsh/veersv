FROM python:3.11-slim

# Install system dependencies for voice support
RUN apt-get update && apt-get install -y \
    libopus0 \
    libopus-dev \
    ffmpeg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
