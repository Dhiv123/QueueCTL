# QueueCTL - CLI Job Queue System

A CLI-based background job queue system built in Python. QueueCTL supports job enqueueing, multiple worker processes, automatic retries with exponential backoff, and a Dead Letter Queue (DLQ) for permanently failed jobs. Jobs persist across restarts.

## Features

Enqueue and manage background jobs

Start multiple worker processes for parallel job execution

Retry failed jobs with configurable exponential backoff

Move jobs to a Dead Letter Queue after exhausting retries

Persistent job storage using SQLite

Clean CLI interface with full configuration management

Minimal testing and demo scripts included

## Setup Instructions
### Prerequisites

Python 3.10+

Git (for cloning the repository)

(Optional) Virtual environment recommended

## Install
### Clone the repository
git clone https://github.com/yourusername/QueueCTL.git
cd QueueCTL

### (Optional) create a virtual environment
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows

## Install dependencies
pip install -r requirements.txt

## Initialize the database
python -m queuectl init

## Usage Examples
### Enqueue a Job
` queuectl enqueue '{"id":"job1","command":"sleep 2"}' `

##Start Workers
### Start 3 workers
` queuectl worker start --count 3 `

### Stop Workers
` queuectl worker stop `

### Check Status
` queuectl status ` 


### Example Output:

Job counts:
  pending: 1
  processing: 0
  completed: 10
  failed: 0
  dead: 2
Worker pidfile: queuectl_workers.pid (pid 12345)

List Jobs by State
queuectl list --state pending
queuectl list --state completed
queuectl list --state dead

## DLQ Commands
### List dead jobs
queuectl dlq list

### Retry a job from DLQ
queuectl dlq retry job1

Configuration
### Set max retries
queuectl config set max-retries 5

### Set backoff base
queuectl config set backoff_base 2

## Architecture Overview
### Job Lifecycle
State	         Description
pending	       Waiting to be picked up by a worker
processing	   Currently being executed
completed	     Successfully executed
failed	       Failed, but retryable
dead	         Permanently failed, moved to DLQ
### Worker Logic

Workers claim jobs atomically from the database (pending or failed jobs ready to run).

Jobs are executed using the system shell.

Exit codes determine job outcome:

0 → mark as completed

non-zero → retry with exponential backoff or move to DLQ after max retries

### Persistence

All jobs and configuration are stored in queue.db using SQLite.

Ensures jobs survive CLI restarts and multiple worker sessions.

## Assumptions & Trade-offs

Commands are executed using the system shell.

SQLite chosen for simplicity and portability

No job priorities implemented in core version (can be added as bonus feature).

Concurrency handled via SQLite transactions (single row claim ensures no duplicate processing).

Backoff formula: delay = backoff_base ** attempts seconds.

## Testing Instructions

### Enqueue a variety of jobs:

queuectl enqueue '{"id":"job_success","command":"echo Hello"}'
queuectl enqueue '{"id":"job_fail","command":"exit 1"}'


### Start workers:

queuectl worker start --count 2


### Verify job states:

queuectl list --state pending
queuectl list --state completed
queuectl dlq list


### Retry DLQ job:

queuectl dlq retry job_fail


### Stop workers:

queuectl worker stop


### Persistence check:

Enqueue a job, close terminal, reopen CLI, and check queuectl list --state pending — the job should still be present.

## Run Demo
Linux/macOS
chmod +x demo_run.sh
./demo_run.sh

Windows (PowerShell / CMD)
demo_run.bat


Demo will:

Enqueue multiple jobs (success, fail, delayed)

Start workers and process jobs

Show job status (pending, completed, dead)

Retry a DLQ job

Test persistence across restart

