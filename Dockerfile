FROM python:3.10-slim

WORKDIR /app

# התקנת כלים בסיסיים
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

COPY . .

EXPOSE 8501

# הוספת הגדרות Streamlit דרך משתני סביבה (יותר יציב מדגלים ב-CMD)
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_WEBSOCKET_COMPRESSION=false

# הפקודה המעודכנת
CMD ["streamlit", "run", "app/ui/app.py"]