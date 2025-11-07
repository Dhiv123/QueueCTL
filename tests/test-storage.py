from queuectl.storage import JobStore

def run():
    s = JobStore()
    s.init_db()   
    jid = s.enqueue({"command": "echo hi"})
    print("Enqueued:", jid)
    job = s.claim_one()
    print("Claimed:", job)
    s.mark_completed(jid)
    print("Completed:", s.get(jid))

if __name__ == "__main__":
    run()
