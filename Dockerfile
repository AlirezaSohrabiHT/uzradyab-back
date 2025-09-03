# Alternative Dockerfile using Supervisor (More Robust)
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install supervisor, cron, and curl
RUN apt-get update && apt-get install -y \
    supervisor \
    cron \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Run migrations
RUN python manage.py migrate

# Create log directories
RUN mkdir -p /var/log/django /var/log/supervisor

# Create cron job file
RUN echo "0 0 * * * cd /app && python manage.py check_expired_devices >> /var/log/django/cron.log 2>&1" > /etc/cron.d/django-tasks && \
    echo "0 18 * * * cd /app && python manage.py send_device_expiry_sms >> /var/log/django/cron.log 2>&1" >> /etc/cron.d/django-tasks && \
    echo "0 2 * * 0 cd /app && python manage.py cleanup_expired_devices --days 30 >> /var/log/django/cron.log 2>&1" >> /etc/cron.d/django-tasks && \
    chmod 0644 /etc/cron.d/django-tasks && \
    crontab /etc/cron.d/django-tasks

# Create supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 36201

# Start supervisor (which will manage both Django and cron)
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]