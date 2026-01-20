FROM python:3.11

WORKDIR /app

# מניעת יצירת קבצי .pyc ושיפור הלוגים
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# פתיחת הפורטים הרלוונטיים
EXPOSE 8000
EXPOSE 8501