# QueueCTL - Design Document
## Overview
QueueCTL is a CLI-based background job queue system that uses SQLite for persistent storage and worker threads for concurrent job processing.
## Core Components
### CLI Layer (cli.py)

Handles all user commands: enqueue, worker, status, list, dlq, config
Parses arguments and delegates to storage/worker modules
Uses Click framework for command-line interface

### Storage Layer (storage.py)

Manages SQLite database operations
Provides methods for enqueuing, claiming, and updating jobs
Uses WAL mode for better concurrency
Implements atomic job claiming with BEGIN IMMEDIATE transactions

### Worker Layer (worker.py)

Runs worker threads that continuously poll for jobs
Executes jobs via subprocess
Handles job completion, failures, and retries
Implements graceful shutdown on SIGTERM/SIGINT

### Utilities (utils.py)

Helper functions for timestamp generation
Shared utility code

## Job Lifecycle
Jobs progress through these states:

pending - Waiting to be picked up
processing - Currently being executed
completed - Successfully finished
failed - Failed but will retry
dead - Permanently failed, moved to DLQ

## Key Design Decisions
### Why SQLite?

Persistent storage without external dependencies
ACID transactions ensure data consistency
WAL mode allows concurrent reads while writing
Single file makes backup and deployment simple

### Why Threads Instead of Processes?

Lower overhead and simpler management
Shared database connection pool
Jobs are I/O bound (subprocess execution) so GIL is not a bottleneck
Easier inter-thread communication for shutdown signals

### How Concurrency is Handled

BEGIN IMMEDIATE transaction locks database during job claiming
Only one worker can claim a specific job at a time
Workers poll every 2 seconds for new jobs
Database-level locking prevents race conditions

### Retry Logic

Exponential backoff formula: delay = base ^ attempts
Default: base=2, max_retries=3
After max retries exceeded, job moves to DLQ
Each retry attempt increments the attempts counter

### Database Schema
jobs table:
  - id: unique job identifier
  - command: shell command to execute
  - state: current job state
  - attempts: number of execution attempts
  - max_retries: maximum retry limit
  - created_at: timestamp when job was created
  - updated_at: timestamp of last state change
  - next_run_at: timestamp when job becomes eligible for execution
  - last_error: error message from last failed attempt

config table:
  - k: configuration key
  - v: configuration value
## Worker Process Flow
Workers follow this loop:

Call claim_one() to atomically claim a pending or failed job
If no job available, sleep for 2 seconds and retry
If job claimed, execute command using subprocess
Check exit code of command
If successful (exit code 0), mark job as completed
If failed, calculate backoff delay and either schedule retry or move to DLQ
Repeat from step 1

## Graceful Shutdown
Workers register signal handlers for SIGTERM and SIGINT. When shutdown signal received:

Set stop flag on all worker threads
Workers finish current job before exiting
No new jobs are claimed
PID file is cleaned up

## Trade-offs and Assumptions
Assumptions:

Jobs are trusted shell commands from administrators
Jobs complete within reasonable timeframes
Single machine deployment
Moderate job volume

## Limitations:

No built-in job timeout mechanism
No job priority support
No job dependency tracking
No distributed worker support
Polling introduces up to 2 second latency

### Why These Limitations:

Keeps implementation simple and maintainable
Satisfies core requirements without overengineering
Can be extended later if needed

## File Structure
QueueCTL/
├── queuectl/
│   ├── __init__.py
│   ├── cli.py
│   ├── storage.py
│   ├── worker.py
│   └── utils.py
├── tests/
│   ├── test_storage.py
│   └── test_worker.py
├── README.md
├── design.md
├── requirements.txt
├── setup.py
├── queue.db (created at runtime)
└── queuectl_workers.pid (created when workers start)
## Testing Approach
Storage operations (enqueue, claim, update)
Worker job execution logic
Retry and backoff calculations
Graceful shutdown behavior
End-to-end job processing
Multiple concurrent workers
Job persistence across restarts
DLQ functionality

Security Considerations
Commands are executed with shell=True, which allows shell features but introduces command injection risk if job data comes from untrusted sources. Current implementation assumes trusted input from CLI only. For production use with untrusted input, command validation and whitelisting should be added.
