
FROM postgres

WORKDIR /db
COPY ./db/ /db/
RUN chmod -R 777 /db

ENV POSTGRES_USER=admin
ENV POSTGRES_PASSWORD=password

RUN mkdir -p /docker-entrypoint-initdb.d/
COPY /db/* /docker-entrypoint-initdb.d/
RUN chmod -R 777 /docker-entrypoint-initdb.d/
