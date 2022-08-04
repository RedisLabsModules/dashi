#!/usr/bin/env bash
while IFS= read -rd '' var; do export "${var}"; done </proc/1/environ
export PYTHONPATH="${PYTHONPATH}:/app"

while true; do
  cd /app && python /app/gather/commits.py > /proc/1/fd/1 2>/proc/1/fd/2
  cd /app && python /app/gather/pipelines.py > /proc/1/fd/1 2>/proc/1/fd/2
  cd /app && python /app/gather/githubActions.py > /proc/1/fd/1 2>/proc/1/fd/2
  sleep "${SLEEP_SECONDS}"
done