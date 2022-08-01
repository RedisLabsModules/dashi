
FROM postgres

WORKDIR /db
COPY ./db/ /db/
RUN chmod -R 777 /db

ENV POSTGRES_USER=admin
ENV POSTGRES_PASSWORD=password
# ENV POSTGRES_MULTIPLE_DATABASES=Merlin-Observation-Log,smart-test

RUN mkdir -p /docker-entrypoint-initdb.d/
COPY /db/* /docker-entrypoint-initdb.d/
RUN chmod -R 777 /docker-entrypoint-initdb.d/
