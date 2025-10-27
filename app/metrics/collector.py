# app/metrics/collector.py
from datetime import datetime


def get_daily_metrics():
    return {"uptime": "OK", "timestamp": datetime().isoformat(), "status": "healthy"}
