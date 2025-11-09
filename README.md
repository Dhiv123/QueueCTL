# QueueCTL - CLI Job Queue System

A CLI-based background job queue system built in Python. QueueCTL supports job enqueueing, multiple worker processes, automatic retries with exponential backoff, and a Dead Letter Queue (DLQ) for permanently failed jobs. Jobs persist across restarts.


## Demo Video

Watch the demo here: [QueueCTL Demo Video](https://drive.google.com/file/d/17UtI3lkbgD6qrxQujDl-JE7c8kDaMoSD/view?usp=sharing)

## Features

- Enqueue and manage background jobs  
- Start multiple worker processes for parallel job execution  
- Retry failed jobs with configurable exponential backoff  
- Move jobs to a Dead Letter Queue after exhausting retries  
- Persistent job storage using SQLite  
- Clean CLI interface with full configuration management  
- Minimal testing and demo scripts included  

## Setup Instructions

### Prerequisites

- Python 3.10+  
- Git (for cloning the repository)  
- (Optional) Virtual environment recommended  

### Clone the repository

```bash
git clone https://github.com/Dhiv123/QueueCTL.git
cd QueueCTL
```
### (Optional) Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows
```
### Install dependencies
```bash
pip install -r requirements.txt
```
### Initialize the database
```bash
python -m queuectl init

```

## Usage Examples
### Enqueue a Job
```bash
queuectl enqueue '{"id":"job1","command":"sleep 2"}'
```
### Start Workers

#### Start 3 workers:
```bash
queuectl worker start --count 3
```

### Stop workers:
```bash
queuectl worker stop
```
### Check Status
```bash
queuectl status
```

#### Example Output:
```bash
Job counts:
  pending: 1
  processing: 0
  completed: 10
  failed: 0
  dead: 2
Worker pidfile: queuectl_workers.pid (pid 12345)
```
### List Jobs by State
```bash
queuectl list --state pending
queuectl list --state completed
queuectl list --state dead
```
### DLQ Commands
List Dead Jobs
```bash
queuectl dlq list
```
### Retry a Job from DLQ
```bash
queuectl dlq retry job1
```
### Configuration
Set Max Retries
```bash
queuectl config set max-retries 5
```
### Set Backoff Base
```bash
queuectl config set backoff_base 2
```
## Architecture Overview

### Job Lifecycle

| State | Description |
|-----------|-------------|
| `pending` | Waiting to be picked up by a worker |
| `processing` | Currently being executed |
| `completed` | Successfully executed |
| `failed` | Failed, but retryable (will retry with backoff) |
| `dead` | Permanently failed, moved to DLQ |

### Job Flow

1. **Enqueue**: Job is created with state `pending`
2. **Claim**: Worker atomically claims a job and marks it `processing`
3. **Execute**: Worker runs the command via subprocess
4. **Result**:
   - **Success** (exit code 0) → state becomes `completed`
   - **Failure** → increments `attempts`, calculates backoff delay
     - If `attempts <= max_retries` → state becomes `failed`, `next_run_at` set to future time
     - If `attempts > max_retries` → state becomes `dead` (moved to DLQ)

### Data Persistence

- **Storage**: SQLite database (`queue.db`)
- **Schema**:
```sql
  jobs (
    id TEXT PRIMARY KEY,
    command TEXT,
    state TEXT,
    attempts INTEGER,
    max_retries INTEGER,
    created_at TEXT,
    updated_at TEXT,
    next_run_at REAL,
    last_error TEXT
  )
```
- **Concurrency**: Uses WAL mode + `BEGIN IMMEDIATE` for atomic job claiming
- **Persistence**: Jobs survive restarts, workers can resume processing

### Worker Logic

- **Multi-threading**: Each worker process runs N threads (configurable via `--count`)
- **Job Claiming**: 
  - Worker loops continuously, calling `claim_one()`
  - `claim_one()` atomically locks and updates one eligible job
  - Only jobs with `next_run_at <= now` are eligible
- **Locking**: Database-level locking prevents duplicate processing
- **Graceful Shutdown**: Workers finish current job before exiting on SIGTERM/SIGINT

### Retry & Backoff

- **Exponential Backoff**: `delay = backoff_base ^ attempts` seconds
- **Default**: base=2, max_retries=3
  - Attempt 1: immediate
  - Attempt 2: retry after 2s
  - Attempt 3: retry after 4s
  - Attempt 4: retry after 8s
  - After attempt 4: moved to DLQ
- **Configurable**: `queuectl config set max-retries N` and `backoff-base N`


## Assumptions & Trade-offs

Commands are executed using the system shell (security trade-off).

SQLite chosen for simplicity and portability.

No job priorities implemented in the core version .

Concurrency handled via SQLite transactions (single row claim ensures no duplicate processing).

Backoff formula: delay = backoff_base ** attempts seconds.

## Testing Instructions
### Enqueue a Variety of Jobs
```bash
queuectl enqueue '{"id":"job_success","command":"echo Hello"}'
queuectl enqueue '{"id":"job_fail","command":"exit 1"}'
```
### Start Workers
```bash
queuectl worker start --count 2
```
### Verify Job States
```bash
queuectl list --state pending
queuectl list --state completed
queuectl dlq list
```
### Retry DLQ Job
```bash
queuectl dlq retry job_fail
```
### Stop Workers
```bash
queuectl worker stop
```
### Persistence Check

Enqueue a job, close terminal, reopen CLI, and check:
```bash
queuectl list --state pending
```
— the job should still be present.

## Run Demo
Linux/macOS
```bash
chmod +x demo_run.sh
./demo_run.sh
```
Windows (PowerShell / CMD)
```bash
demo_run.bat
```

### Demo will:

Enqueue multiple jobs (success, fail, delayed)

Start workers and process jobs

Show job status (pending, completed, dead)

Retry a DLQ job

Test persistence across restart


