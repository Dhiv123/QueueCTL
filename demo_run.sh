#!/bin/bash

echo "=== QueueCTL Demo Script ==="

# Enqueue jobs
echo "Enqueueing jobs..."
queuectl enqueue '{"id":"job_demo_1","command":"echo Hello"}'
queuectl enqueue '{"id":"job_demo_2","command":"exit 1"}'
queuectl enqueue '{"id":"job_demo_3","command":"sleep 2"}'

#  Start workers
echo "Starting 2 workers..."
queuectl worker start --count 2

# Wait for jobs to process
sleep 5

#  Show status
echo "Queue status after processing:"
queuectl status

#  List completed jobs
echo "Completed jobs:"
queuectl list --state completed

#  List pending jobs
echo "Pending jobs:"
queuectl list --state pending

#  List dead jobs
echo "Dead jobs (DLQ):"
queuectl dlq list

#  Retry a dead job
echo "Retrying a DLQ job (job_demo_2)..."
queuectl dlq retry job_demo_2

# Wait for retry to process
sleep 5

echo "Status after retry:"
queuectl status

#  Persistence test
echo "Persistence test: restart CLI simulation..."
queuectl enqueue '{"id":"job_demo_persist","command":"sleep 1"}'
echo "Simulating restart... (close and reopen CLI)"
queuectl list --state pending

echo "=== Demo Completed ==="
