#!/usr/bin/env bash

while IFS= read -rd '' var; do export "${var}"; done </proc/1/environ
cd /app/ && /usr/local/bin/python /app/gather.py > /proc/1/fd/1 2>/proc/1/fd/2