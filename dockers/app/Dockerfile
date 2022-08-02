FROM python:latest

WORKDIR /app
ADD . /app

RUN apt-get -qq update && apt-get -y install cron postgresql-client
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt

RUN cp -v /app/dockers/app/cronfile /etc/cron.d/cron
RUN chmod 0644 /etc/cron.d/cron
RUN crontab /etc/cron.d/cron

ENTRYPOINT ["/app/dockers/app/entrypoint.sh"]
