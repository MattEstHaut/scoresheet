FROM python:alpine3.20

WORKDIR /app
COPY app/ /app/

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

CMD ["python3", "api.py"]