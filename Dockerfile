# Python 3.11 slim base image kullan
FROM python:3.11-slim

# Çalışma dizinini ayarla
WORKDIR /app

# Sistem paketlerini güncelle ve gerekli paketleri yükle
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Requirements dosyasını kopyala ve bağımlılıkları yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Gerekli dizinleri oluştur
RUN mkdir -p migrations/versions

# Çevre değişkenlerini ayarla
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Port ayarla
EXPOSE 5001

# Veritabanını hazırla (eğer yoksa)
RUN python -c "
import os
from app import app, db
with app.app_context():
    if not os.path.exists('debate_arena.db'):
        db.create_all()
        print('✅ Database created successfully!')
    else:
        print('ℹ️  Database already exists.')
"

# Health check ekle
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5001/ || exit 1

# Uygulamayı çalıştır
CMD ["python", "app.py"]