# worker.py - manages worker processes that process jobs from the JobStore
import subprocess
import time
from queuectl.storage import JobStore
import argparse
import os
import signal
import sys

class Worker:
    def __init__(self, store: JobStore, worker_id: int):
        self.store = store
        self.worker_id = worker_id
        self.stop_flag = False

    def run_job(self, job):
        job_id = job["id"]
        cmd = job["command"]
        print(f"[Worker {self.worker_id}] Running job {job_id}: {cmd}")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(result.stdout.strip())
                self.store.mark_completed(job_id)
                print(f"[Worker {self.worker_id}] Job {job_id} completed")
            else:
                raise Exception("Command failed")
        except Exception as e:
            print(f"[Worker {self.worker_id}] Job {job_id} failed ({e})")
            self.store.schedule_retry_or_dead(
                job_id,
                job["attempts"],
                job["max_retries"],
                str(e),
            )

    def loop(self):
        while not self.stop_flag:
            job = self.store.claim_one()
            if job:
                self.run_job(job)
            else:
                time.sleep(2)

    def stop(self):
        self.stop_flag = True


PIDFILE = "queuectl_workers.pid"

def run_worker_blocking(worker_id=1):
    """Start a single worker in this process (blocking)."""
    store = JobStore()
    store.init_db()
    
    w = Worker(store, worker_id)

    # handle SIGTERM 
    def _term_handler(signum, frame):
        print(f"Worker {worker_id} received termination signal, shutting down...")
        w.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _term_handler)
    signal.signal(signal.SIGINT, _term_handler)

    # block and run the worker loop
    try:
        w.loop()
    except KeyboardInterrupt:
        print(f"\nWorker {worker_id} shutting down...")
        w.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QueueCTL worker process")
    parser.add_argument("--id", type=int, default=1, help="worker ID for this process")
    args = parser.parse_args()
    run_worker_blocking(worker_id=args.id)