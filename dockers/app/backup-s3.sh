#!/usr/bin/env bash

DATE=$(date +%Y%m%d)
DUMP_PATH=/tmp

docker exec $(docker ps -a | grep db | awk '{print $NF}') pg_dump -h localhost -Uadmin -d admin --clean > "${DUMP_PATH}"/dump-"${DATE}".sql

tar czvf /tmp/dump-"${DATE}".tgz /tmp/dump-"${DATE}".sql

aws s3 cp "${DUMP_PATH}"/dump-"${DATE}".tgz s3://BUCKUP_BUCKET/

if [[ -f ${DUMP_PATH}/${DATE}.tgz ]]; then
  rm -rf "${DUMP_PATH}"/"${DATE}".tgz
  rm -rf "${DUMP_PATH}"/"${DATE}".sql
fi
