@echo off
echo === QueueCTL Demo Script ===

REM  Enqueue jobs
echo Enqueueing jobs...
queuectl enqueue "{\"id\":\"job_demo_1\",\"command\":\"echo Hello\"}"
queuectl enqueue "{\"id\":\"job_demo_2\",\"command\":\"exit 1\"}"
queuectl enqueue "{\"id\":\"job_demo_3\",\"command\":\"timeout /t 2\"}"

REM  Start workers
echo Starting 2 workers...
queuectl worker start --count 2

REM Wait for jobs to process
timeout /t 5

REM  Show status
echo Queue status after processing:
queuectl status

REM  List completed jobs
echo Completed jobs:
queuectl list --state completed

REM  List pending jobs
echo Pending jobs:
queuectl list --state pending

REM  List dead jobs
echo Dead jobs (DLQ):
queuectl dlq list

REM Retry a dead job
echo Retrying a DLQ job (job_demo_2)...
queuectl dlq retry job_demo_2


echo Status after retry:
queuectl status

REM  Persistence test
echo Persistence test: enqueue job_demo_persist...
queuectl enqueue "{\"id\":\"job_demo_persist\",\"command\":\"timeout /t 1\"}"
echo Simulating restart...
queuectl list --state pending

echo === Demo Completed ===
pause
