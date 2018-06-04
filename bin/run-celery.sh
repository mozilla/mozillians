#!/bin/bash

# Run default celery worker
conc=$(($(nproc) / 2))
celery -A mozillians worker -Q celery -l INFO -n default@%h -c $conc &
status=$?

if [ $status -ne 0 ]; then
    echo "Failed to start default worker: $status"
    exit $status
fi

# Run cis celery worker
celery -A mozillians worker -Q cis -l INFO -n cis@%h -Ofair -c $conc &
status=$?
if [ $status -ne 0 ]; then
    echo "Failed to start cis worker: $status"
    exit $status
fi

# Check if one of the runners exited
while sleep 60; do
    ps aux | grep -e "-Q celery" | grep -q -v grep
    WORKER_1_STATUS=$?

    ps aux | grep -e "-Q cis" | grep -q -v grep
    WORKER_2_STATUS=$?

    if [ $WORKER_1_STATUS -ne 0 -o $WORKER_2_STATUS -ne 0 ]; then
        echo "One of the workers has already exited."
        exit 1
    fi
done
