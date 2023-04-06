#!/usr/bin/env bash
while IFS= read -rd '' var; do export "${var}"; done </proc/1/environ
export PYTHONPATH="${PYTHONPATH}:/app"

cd /app && python /app/gather/commits.py > /proc/1/fd/1 2>/proc/1/fd/2
cd /app && python /app/gather/pipelines.py > /proc/1/fd/1 2>/proc/1/fd/2
cd /app && python /app/gather/githubActions.py > /proc/1/fd/1 2>/proc/1/fd/2
