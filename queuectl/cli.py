# queuectl/cli.py
import json
import os
import signal
import subprocess
import sys
import time
from typing import Optional

import click
from .storage import JobStore
from .utils import now_ts, iso_now  

PIDFILE = "queuectl_workers.pid"

@click.group()
def main():
    """QueueCTL - CLI-based background job queue system."""
    pass

# ENQUEUE

@main.command()
@click.argument("job_json", type=str)
def enqueue(job_json):
    """Add a new job to the queue."""
    store = JobStore()
    store.init_db()
    try:
        # Try parsing normally
        job = json.loads(job_json)
    except json.JSONDecodeError:
        # PowerShell/CMD safe fallback: fix stripped quotes
        fixed = job_json.strip()
        if fixed.startswith("{") and not '"' in fixed:
            # Replace single quotes with double quotes
            fixed = fixed.replace("'", '"')
        try:
            job = json.loads(fixed)
        except Exception as e:
            click.echo(f"Invalid JSON: {e}", err=True)
            sys.exit(2)
    jid = store.enqueue(job)
    click.echo(jid)


# WORKER COMMANDS

@main.group()
def worker():
    #Manage worker processes
    pass

@worker.command("start")
@click.option("--count", "-c", default=1, help="Number of worker threads inside worker process")
@click.option("--processes", "-p", default=1, help="How many worker processes to spawn (each process runs --count threads)")
def worker_start(count: int, processes: int):
    #Start one or more worker processes.
    procs = []
    for i in range(processes):
        cmd = [sys.executable, "-m", "queuectl.worker", "--count", str(count)]
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append(p.pid)
    click.echo(f"Spawned worker processes: {procs}")
    click.echo(f"Worker pidfile location: {os.path.abspath(PIDFILE)}")

@worker.command("stop")
def worker_stop():
    #Stop worker processes using pidfile
    if not os.path.exists(PIDFILE):
        click.echo("No worker pidfile found; maybe workers already stopped.")
        return

    try:
        with open(PIDFILE, "r") as f:
            pid = int(f.read().strip().splitlines()[0])
        click.echo(f"Stopping worker process pid={pid} ...")

        if os.name == "nt":  
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(pid, signal.SIGTERM)

        # Wait briefly for the process to end
        time.sleep(1.5)

        # Cleanup leftover pidfile manually
        if os.path.exists(PIDFILE):
            try:
                os.remove(PIDFILE)
                click.echo("Worker stopped and pidfile cleaned.")
            except Exception:
                click.echo("Worker stopped but could not remove pidfile.")
        else:
            click.echo("Stopped successfully.")

    except Exception as e:
        click.echo(f"Error stopping workers: {e}", err=True)

# LIST & STATUS COMMANDS

@main.command("list")
@click.option("--state", type=click.Choice(["pending", "processing", "completed", "failed", "dead"]), default=None)
def list_jobs(state: Optional[str]):
    """List jobs by state (or all if no --state)."""
    store = JobStore()
    store.init_db()
    rows = store.list_by_state(state) if state else store.list_by_state(None)
    for r in rows:
        click.echo(json.dumps(r))

@main.command("status")
def status():
    """Show summary of all job states and active workers."""
    store = JobStore()
    store.init_db()
    counts = {s: len(store.list_by_state(s)) for s in ["pending", "processing", "completed", "failed", "dead"]}
    click.echo("Job counts:")
    for k, v in counts.items():
        click.echo(f"  {k}: {v}")
    if os.path.exists(PIDFILE):
        with open(PIDFILE, "r") as f:
            pid = f.read().strip().splitlines()[0]
        click.echo(f"Worker pidfile: {PIDFILE} (pid {pid})")
    else:
        click.echo("No worker pidfile found.")

# DLQ COMMANDS

@main.group()
def dlq():

    pass

@dlq.command("list")
def dlq_list():
    #List jobs in DLQ.
    store = JobStore()
    store.init_db()
    rows = store.list_by_state("dead")
    for r in rows:
        click.echo(json.dumps(r))

@dlq.command("retry")
@click.argument("job_id")
def dlq_retry(job_id):
    #Retry a job from DLQ
    store = JobStore()
    store.init_db()
    job = store.get(job_id)
    if not job:
        click.echo("job not found", err=True)
        return
    if job["state"] != "dead":
        click.echo("job is not in DLQ", err=True)
        return

    conn = store._conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE jobs SET state=?, attempts=?, next_run_at=?, updated_at=? WHERE id=?",
        ("pending", 0, now_ts(), iso_now(), job_id),
    )
    conn.commit()
    conn.close()
    click.echo(f"Retried job {job_id}")

# CONFIG COMMANDS

@main.group()
def config():

    pass

@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    #Set configuration key
    store = JobStore()
    store.init_db()
    store.config_set(key, value)
    click.echo(f"{key} = {value}")

@config.command("get")
@click.argument("key")
def config_get(key):
    #Get configuration key
    store = JobStore()
    store.init_db()
    val = store.config_get(key)
    click.echo(val if val is not None else "")

if __name__ == "__main__":
    main()