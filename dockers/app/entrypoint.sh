#!/bin/bash -e

# PATH=$PATH:/usr/local/bin

DB_HOST="$(echo ${DATABASE_URL} | sed -E -n 's/.*\@(.*)\:\b[0-9]{4,5}/\1/p')"

until pg_isready -h $DB_HOST; do
	echo "Waiting for db ${DB_HOST} ..."
	sleep 1
done

if [[ -z $GITHUB_TOKEN ]]; then
	flask db upgrade
else
	until curl http://app:5000 -s -f -o /dev/null; do
		echo "wait until service is up..."
	done
fi

exec "$@"
