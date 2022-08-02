#!/bin/bash -ex

PATH=$PATH:/usr/local/bin

DB_HOST="$(echo ${DATABASE_URL} | sed -E -n 's/.*\@(.*)\:\b[0-9]{4,5}/\1/p')"

until pg_isready -h $DB_HOST; do
	echo "Waiting for db ${DB_HOST} ..."
	sleep 1
done
flask db upgrade

exec "$@"
