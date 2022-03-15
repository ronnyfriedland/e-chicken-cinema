FROM python:3-slim-buster

EXPOSE 8000

WORKDIR /usr/src/app

COPY src .
COPY requirements.txt .

RUN pip3 install --no-cache-dir --requirement requirements.txt

CMD python ./e-chicken-cinema.py
