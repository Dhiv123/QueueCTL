import datetime

def now_ts():
    # Return current UTC timestamp as float
    return datetime.datetime.utcnow().timestamp()

def iso_now():
    # Return current UTC time in ISO format
    return datetime.datetime.utcnow().isoformat()
