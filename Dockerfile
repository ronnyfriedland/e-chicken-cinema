FROM arm64v8/python:3-slim-bullseye

EXPOSE 8000

WORKDIR /usr/src/app

COPY src .
COPY requirements.txt .

# allow docker build on non raspberry hardware
ENV READTHEDOCS=True

RUN pip3 install --no-cache-dir --requirement requirements.txt

CMD python ./e-chicken-cinema.py
