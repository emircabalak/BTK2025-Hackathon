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
ENV PYTHONUNBUFFERED=1

# Port ayarla
EXPOSE 5001

# Veritabanını hazırla (güvenli şekilde)
RUN python -c "
import os
import sys
sys.path.append('/app')
try:
    from app import app, db
    with app.app_context():
        if not os.path.exists('/app/debate_arena.db'):
            db.create_all()
            print('✅ Database created successfully!')
        else:
            print('ℹ️  Database already exists.')
except Exception as e:
    print(f'⚠️  Database initialization error: {e}')
    # Continue anyway, app will handle it
"

# Health check ekle (internal container address kullan)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://127.0.0.1:5001/ || exit 1

# Non-root user oluştur (güvenlik için)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Uygulamayı çalıştır
CMD ["python", "app.py"]