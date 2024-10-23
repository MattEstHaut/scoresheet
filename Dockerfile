FROM python:alpine3.20

WORKDIR /app
COPY app/ /app/

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

EXPOSE 80

CMD ["fastapi", "run", "api.py", "--port", "80"]
