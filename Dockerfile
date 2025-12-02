FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/
EXPOSE 36201
CMD ["uvicorn", "uzerp.asgi:application", "--host", "0.0.0.0", "--port", "8327", "--limit-max-requests", "0", "--timeout-keep-alive", "120"]
