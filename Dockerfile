# Menggunakan base image Python 3.10 slim
FROM python:3.10-slim

# Mengatur environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (ffmpeg sangat penting untuk pydub dan Whisper)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory di dalam container
WORKDIR /app

# Menyalin file requirements.txt
COPY requirements.txt .

# Upgrade pip dan install requirements dasar
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Install PyTorch dan library Machine Learning tambahan
# Catatan: Secara default pip install torch di Linux akan menyertakan CUDA support (berukuran cukup besar).
RUN pip install --no-cache-dir torch torchaudio torchvision
RUN pip install --no-cache-dir faster-whisper whisperx

# Install library tambahan untuk pengecekan GPU (sesuai yang digunakan di main.py)
RUN pip install --no-cache-dir nvidia-ml-py3 nvidia-smi

# Menyalin seluruh kode proyek
COPY . .

# Menjalankan aplikasi
CMD ["python", "main.py"]
