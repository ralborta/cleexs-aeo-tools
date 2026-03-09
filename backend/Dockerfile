# Backend Cleexs AEO Toolkit - Railway
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Railway injects PORT at runtime
ENV PORT=8000
EXPOSE 8000

# Railway sets PORT at runtime; use shell form so it expands
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
