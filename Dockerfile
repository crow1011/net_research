FROM python:3.8-slim

COPY . /app
WORKDIR /app

RUN pip3 install --no-cache-dir  -r requirements.txt

CMD ["python3", "-u", "main.py"]