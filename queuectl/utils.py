import datetime

def now_ts():
    """Return current UTC timestamp as float (seconds)."""
    return datetime.datetime.utcnow().timestamp()

def iso_now():
    """Return current UTC time in ISO 8601 format (string)."""
    return datetime.datetime.utcnow().isoformat()
