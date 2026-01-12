FROM python:3.10-slim

WORKDIR /app

# מעתיקים קודם רק את ה-requirements
COPY requirements.txt .

# מגדילים את ה-timeout ומתקינים
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# רק עכשיו מעתיקים את כל השאר
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app/ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]