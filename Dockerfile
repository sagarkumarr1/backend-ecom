FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --no-input --settings=jwtproject.settings.production

EXPOSE 8000

CMD ["gunicorn", "jwtproject.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
