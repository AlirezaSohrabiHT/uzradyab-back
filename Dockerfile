FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
# Copy requirements and try to install without build tools
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
# If the above fails, you need build tools
# If it succeeds, you can use this minimal approach
COPY . /app/
RUN python manage.py migrate
EXPOSE 8756
CMD ["uvicorn", "managerPanel.asgi:application", "--host", "0.0.0.0", "--port", "36201"]
