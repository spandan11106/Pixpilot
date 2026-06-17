FROM python:3.11-alpine

RUN apk add --no-cache ffmpeg

WORKDIR /app

RUN pip install fastapi uvicorn[standard]

COPY server.py .

EXPOSE 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
