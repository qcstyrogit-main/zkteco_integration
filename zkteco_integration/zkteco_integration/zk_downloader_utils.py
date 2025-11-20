import frappe
from datetime import datetime
from datetime import timedelta

def clean_duplicate_logs(logs, threshold_seconds=60):
    """
    Clean duplicate attendance logs that are too close in time per user.
    Args:
        logs: List of attendance log objects
        threshold_seconds: Number of seconds within which logs are considered duplicates (default 60)
    Returns:
        List of logs with near-time duplicates removed
    """
    if not logs:
        return []
    
    # Sort logs by user_id and timestamp
    sorted_logs = sorted(logs, key=lambda x: (x.user_id, x.timestamp))
    cleaned_logs = []
    last_timestamp_per_user = {}

    for log in sorted_logs:
        last_time = last_timestamp_per_user.get(log.user_id)

        if last_time:
            time_diff = (log.timestamp - last_time).total_seconds()
            if time_diff <= threshold_seconds:
                # Skip duplicate within threshold
                continue
        
        # Keep the log and update last timestamp
        cleaned_logs.append(log)
        last_timestamp_per_user[log.user_id] = log.timestamp

    return cleaned_logs

def check_existing_checkin(employee, log_time):
    """
    Check if an Employee Checkin already exists for the employee on the same day.
    Args:
        employee: Employee name
        log_time: datetime object
    Returns:
        True if exists, False otherwise
    """
    # Consider a checkin a duplicate if it exists within +/- 60 seconds of the log_time
    threshold_seconds = 60
    start = log_time - timedelta(seconds=threshold_seconds)
    end = log_time + timedelta(seconds=threshold_seconds)

    # Use a query with range conditions to find any matching checkin
    exists = frappe.db.exists(
        "Employee Checkin",
        [
            ["employee", "=", employee],
            ["time", ">=", start],
            ["time", "<=", end],
        ],
    )
    return bool(exists)
