#!/bin/bash

N=$1

if [ -z "$N" ]; then
    echo "Usage: $0 <number_of_processes>"
    exit 1
fi

for i in $(seq 1 $N); do
    bash bin/run-client.sh &
    echo "Started process $i (PID: $!)"
done

wait
echo "All $N processes finished"