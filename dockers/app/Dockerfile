FROM python:latest

WORKDIR /app
ADD . /app

RUN apt-get -qq update && \
    apt-get -y install postgresql-client && \
    rm -rf /var/lib/apt/lists/*
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt

ENTRYPOINT ["/app/dockers/app/entrypoint.sh"]
