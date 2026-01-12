FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/ ./proto/
COPY server.py .
COPY temperature_controller.py .

EXPOSE 50051

CMD ["python", "server.py"]
