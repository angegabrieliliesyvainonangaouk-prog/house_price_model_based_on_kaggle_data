FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY prediction.py .
COPY prediction_cleaner.py .
COPY modele.ml/ modele.ml/
COPY server.py .
COPY auth.py .
COPY email_service.py .
COPY frontend/ frontend/

EXPOSE 8000

CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
