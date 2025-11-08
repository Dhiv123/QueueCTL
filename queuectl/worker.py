# worker.py - manages worker threads that process jobs from the JobStore
import subprocess
import threading
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


def start_workers(count=2):
    store = JobStore()
    store.init_db()
    threads = []
    for i in range(count):
        w = Worker(store, i + 1)
        t = threading.Thread(target=w.loop, daemon=True)
        threads.append(t)
        t.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down workers...")
        for t in threads:
            t.join(timeout=2)


PIDFILE = "queuectl_workers.pid"

def run_workers_blocking(count=1):
    """Start 'count' worker threads in this process (blocking)."""
    store = JobStore()
    store.init_db()
    threads = []
    workers = []
    for i in range(count):
        w = Worker(store, i + 1)
        t = threading.Thread(target=w.loop, daemon=True)
        threads.append(t)
        workers.append(w)
        t.start()

    # write pidfile for supervisor CLI to stop later
    try:
        with open(PIDFILE, "w") as f:
            f.write(str(os.getpid()) + "\n")
    except Exception:
        pass

    # handle SIGTERM 
    def _term_handler(signum, frame):
        print("Worker process received termination signal, shutting down...")
        for w in workers:
            w.stop()

    signal.signal(signal.SIGTERM, _term_handler)
    signal.signal(signal.SIGINT, _term_handler)

    # block until threads exit
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(0.5)
    finally:
        # cleanup pidfile
        try:
            if os.path.exists(PIDFILE):
                os.remove(PIDFILE)
        except Exception:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QueueCTL worker process")
    parser.add_argument("--count", "-c", type=int, default=1, help="number of worker threads to start in this process")
    args = parser.parse_args()
    run_workers_blocking(count=args.count)
   