from queuectl.storage import JobStore
from queuectl.worker import start_workers
import time

store = JobStore()
store.enqueue({"command": "echo Hello"})
store.enqueue({"command": "exit 1"})  
start_workers(count=2)

time.sleep(10)  
