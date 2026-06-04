import frappe
import socket
from zk import ZK
from datetime import datetime, timedelta
from .zk_downloader_utils import clean_duplicate_logs, check_existing_checkin


@frappe.whitelist()
def test_connection(device_name):
    """Test TCP + ZK connection for a single ZKTeco Device and return status."""
    dev = frappe.get_doc("ZKTeco Device", device_name)
    ip = dev.device_ip
    port = int(dev.port or 4370)

    # TCP reachability check first
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, port))
        sock.close()
        if result != 0:
            return {"success": False, "message": f"Device {ip}:{port} is not reachable (TCP check failed)."}
    except Exception as e:
        return {"success": False, "message": f"TCP error: {str(e)}"}

    # ZK protocol handshake
    try:
        zk = ZK(ip, port=port, timeout=5, password="0")
        conn = zk.connect()
        firmware = conn.get_firmware_version() if hasattr(conn, "get_firmware_version") else "N/A"
        serial = conn.get_serialnumber() if hasattr(conn, "get_serialnumber") else "N/A"
        conn.disconnect()
        return {
            "success": True,
            "message": f"Connected successfully to {ip}:{port}",
            "firmware": firmware,
            "serial": serial,
        }
    except Exception as e:
        return {"success": False, "message": f"ZK connection error: {str(e)}"}


@frappe.whitelist()
def fetch_attendance_for_device(device_name, start_date=None, end_date=None):
    """Fetch and insert attendance logs for a single ZKTeco Device."""
    dev = frappe.get_doc("ZKTeco Device", device_name)

    summary = {
        "devices_processed": 0,
        "total_logs": 0,
        "inserted_logs": 0,
        "skipped_duplicates": 0,
        "missing_employees": 0,
        "errors": [],
    }

    try:
        zk = ZK(dev.device_ip, port=int(dev.port or 4370), timeout=10, password="0")
        conn = zk.connect()
        attendances = conn.get_attendance()
        conn.disconnect()

        last_sync = dev.last_sync
        if last_sync:
            last_sync = last_sync if isinstance(last_sync, datetime) else datetime.strptime(str(last_sync), "%Y-%m-%d %H:%M:%S")
        else:
            last_sync = datetime(1970, 1, 1)

        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d") if isinstance(start_date, str) else start_date
        else:
            start_date = last_sync
        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1) if isinstance(end_date, str) else end_date
        else:
            end_date = datetime.now()

        filtered_logs = [log for log in attendances if hasattr(log, "timestamp") and start_date <= log.timestamp <= end_date]
        unique_logs = clean_duplicate_logs(filtered_logs, threshold_seconds=30)

        summary["devices_processed"] = 1
        summary["total_logs"] = len(unique_logs)

        for att in unique_logs:
            attendance_device_id = f"{dev.machine_no}-{att.user_id}"
            employee = frappe.db.get_value("Employee", {"attendance_device_id": attendance_device_id, "status": "Active"}, "name")
            if not employee:
                frappe.log_error(f"No Employee found for attendance_device_id {attendance_device_id}", "ZK Downloader")
                summary["missing_employees"] += 1
                continue

            if check_existing_checkin(employee, att.timestamp):
                summary["skipped_duplicates"] += 1
                continue

            checkin = frappe.get_doc({
                "doctype": "Employee Checkin",
                "employee": employee,
                "time": att.timestamp,
                "device_id": getattr(dev, "device_id", dev.name),
                "log_type": None,
            })
            checkin.fetch_shift()

            log_type = None
            last_log = frappe.db.get_value("Employee Checkin", {"employee": employee}, ["log_type", "time"], order_by="time desc")

            if hasattr(checkin, "shift_start") and hasattr(checkin, "shift_end") and checkin.shift_start and checkin.shift_end:
                shift_start = checkin.shift_start
                shift_end = checkin.shift_end
                if shift_end < shift_start:
                    shift_end += timedelta(days=1)
                if abs((att.timestamp - shift_start).total_seconds()) <= 4 * 3600:
                    log_type = "IN"
                elif abs((att.timestamp - shift_end).total_seconds()) <= 4 * 3600:
                    log_type = "OUT"

            if not log_type and last_log:
                log_type = "OUT" if last_log[0] == "IN" else "IN"
            elif not log_type:
                log_type = "IN"

            checkin.log_type = log_type
            checkin.insert(ignore_permissions=True)
            frappe.db.commit()
            summary["inserted_logs"] += 1

        frappe.db.set_value("ZKTeco Device", device_name, "last_sync", datetime.now())
        frappe.db.commit()
        summary["success"] = True

    except Exception as e:
        error_msg = f"Error processing device {dev.device_ip}: {str(e)}"
        summary["errors"].append(error_msg)
        frappe.log_error(error_msg, "ZK Downloader")
        summary["success"] = False

    return summary


@frappe.whitelist()
def fetch_and_insert_attendance_logs(start_date=None, end_date=None):
    """
    Fetch logs from all active ZKTeco devices and insert into Employee Checkin.
    This function is intended to be used as a scheduled job in ERPNext.
    Optionally, fetch logs within a date range (start_date, end_date as datetime or string).
    Returns a summary dict for UI display.
    """
    devices = frappe.get_all(
        "ZKTeco Device",
        filters={"status": 1},  # 1 = checked/active
        fields=["name", "device_ip", "port", "machine_no", "last_sync", "device_id"]
    )
    if not devices:
        frappe.log_error("No active ZKTeco devices found.", "ZK Downloader")
        return {"success": False, "message": "No active devices found."}

    summary = {
        "devices_processed": 0,
        "total_logs": 0,
        "inserted_logs": 0,
        "skipped_duplicates": 0,
        "missing_employees": 0,
        "errors": []
    }

    for dev in devices:
        try:
            zk = ZK(dev.device_ip, port=int(dev.port or 4370), timeout=10, password="0")
            conn = zk.connect()
            attendances = conn.get_attendance()
            conn.disconnect()

            # Get last sync time from device record
            last_sync = dev.get("last_sync")
            if last_sync:
                last_sync = last_sync if isinstance(last_sync, datetime) else datetime.strptime(str(last_sync), "%Y-%m-%d %H:%M:%S")
            else:
                last_sync = datetime(1970, 1, 1)

            # Date range filtering
            if start_date:
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                start_date = last_sync
            if end_date:
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
            else:
                end_date = datetime.now()

            filtered_logs = [log for log in attendances if hasattr(log, 'timestamp') and start_date <= log.timestamp <= end_date]
            # Clean duplicates (logs within 60 seconds of each other)
            unique_logs = clean_duplicate_logs(filtered_logs, threshold_seconds=30)

            summary["devices_processed"] += 1
            summary["total_logs"] += len(unique_logs)

            for att in unique_logs:
                attendance_device_id = f"{dev.machine_no}-{att.user_id}"
                employee = frappe.db.get_value("Employee", {"attendance_device_id": attendance_device_id, "status": "Active"}, "name")
                if not employee:
                    frappe.log_error(f"No Employee found for attendance_device_id {attendance_device_id}", "ZK Downloader")
                    summary["missing_employees"] += 1
                    continue

                # Prevent duplicate checkin for the same employee and day
                if check_existing_checkin(employee, att.timestamp):
                    summary["skipped_duplicates"] += 1
                    continue

                # Prepare checkin doc
                checkin = frappe.get_doc({
                    "doctype": "Employee Checkin",
                    "employee": employee,
                    "time": att.timestamp,
                    "device_id": getattr(dev, 'device_id', dev.name),
                    "log_type": None
                })

                # Fetch shift before deciding log_type
                checkin.fetch_shift()

                log_type = None

                # --- 1. Check for last checkin of employee ---
                last_log = frappe.db.get_value(
                    "Employee Checkin",
                    {"employee": employee},
                    ["log_type", "time"],
                    order_by="time desc"
                )

                # --- 2. Use shift window to refine IN/OUT detection ---
                if hasattr(checkin, "shift_start") and hasattr(checkin, "shift_end") and checkin.shift_start and checkin.shift_end:
                    shift_start = checkin.shift_start
                    shift_end = checkin.shift_end

                    # Handle overnight shift
                    if shift_end < shift_start:
                        shift_end += timedelta(days=1)

                    # Time proximity logic (4 hours before/after window)
                    if abs((att.timestamp - shift_start).total_seconds()) <= 4 * 3600:
                        log_type = "IN"
                    elif abs((att.timestamp - shift_end).total_seconds()) <= 4 * 3600:
                        log_type = "OUT"

                # --- 3. Fallback: alternate based on last log ---
                if not log_type and last_log:
                    last_log_type = last_log[0]
                    log_type = "OUT" if last_log_type == "IN" else "IN"
                elif not log_type:
                    log_type = "IN"  # first ever log → assume IN

                checkin.log_type = log_type

                # Insert checkin
                checkin.insert(ignore_permissions=True)
                frappe.db.commit()
                summary["inserted_logs"] += 1

            # Update last_sync
            frappe.db.set_value("ZKTeco Device", dev.name, "last_sync", datetime.now())
        except Exception as e:
            error_msg = f"Error processing device {dev.device_ip}: {str(e)}"
            summary["errors"].append(error_msg)
            frappe.log_error(error_msg, "ZK Downloader")

    frappe.db.commit()
    summary["success"] = True
    return summary

# Example usage:
# fetch_and_insert_attendance_logs("2025-10-01", "2025-10-23")
