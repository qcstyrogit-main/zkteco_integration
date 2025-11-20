import frappe
from zk import ZK, const
from datetime import datetime
import socket

class ZKTecoLogDownloader(frappe.model.document.Document):
    pass  # class left empty, method moved outside

def check_device_connectivity(ip_address, port):
    """
    Check if the device is reachable at the given IP address and port.
    Returns: bool - True if device is reachable, False otherwise
    """
    try:
        # Create a socket object with a timeout of 3 seconds
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        
        # Attempt to connect to the device
        result = sock.connect_ex((ip_address, int(port)))
        sock.close()
        
        return result == 0  # If result is 0, connection was successful
    except Exception as e:
        frappe.logger().error(f"Connection check failed for {ip_address}:{port} - {str(e)}")
        return False
    
def get_new_attendance_logs(self, last_timestamp):
    """
    Get only attendance logs with timestamp greater than last_timestamp.
    Args:
        last_timestamp: datetime or string in '%Y-%m-%d %H:%M:%S' format
    Returns:
        List of new attendance records
    """
    if isinstance(last_timestamp, str):
        last_timestamp = datetime.strptime(last_timestamp, '%Y-%m-%d %H:%M:%S')
    logs = self.get_attendance_logs()
    new_logs = [log for log in logs if hasattr(log, 'timestamp') and log.timestamp > last_timestamp]
    return new_logs

def get_attendance_logs_by_range(self, start_datetime, end_datetime):
    """
    Get attendance logs within a date range.
    Args:
        start_datetime: datetime or string in '%Y-%m-%d %H:%M:%S' format
        end_datetime: datetime or string in '%Y-%m-%d %H:%M:%S' format
    Returns:
        List of attendance records in the range
    """
    if isinstance(start_datetime, str):
        start_datetime = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
    if isinstance(end_datetime, str):
        end_datetime = datetime.strptime(end_datetime, '%Y-%m-%d %H:%M:%S')
    logs = self.get_attendance_logs()
    range_logs = [log for log in logs if hasattr(log, 'timestamp') and start_datetime <= log.timestamp <= end_datetime]
    return range_logs


# -------------------------------
# Module-level function
# -------------------------------
@frappe.whitelist()


def download_all_logs():
    """
    Downloads logs from all active ZKTeco devices.
    Can be called from client script or API.
    """
    devices = frappe.get_all(
        "ZKTeco Device",
        filters={"status": "Active"},
        fields=["name", "device_ip", "port"]
    )

    if not devices:
        frappe.msgprint("No active ZKTeco devices found.")
        return "No active devices."

    total_logs = 0

    for dev in devices:
        frappe.msgprint(f"Checking connection to device {dev.name} ({dev.device_ip})...")
        
        # Check device connectivity before attempting to download logs
        if not check_device_connectivity(dev.device_ip, int(dev.port or 4370)):
            frappe.msgprint(f"Device {dev.name} ({dev.device_ip}) is not reachable.")
            frappe.log_error(
                f"Device {dev.name} ({dev.device_ip}) is not reachable",
                "ZKTeco Connection Error"
            )
            continue

        frappe.msgprint(f"Connecting to device {dev.name} ({dev.device_ip})...")
        try:
            zk = ZK(dev.device_ip, port=int(dev.port or 4370), timeout=5,password="0")
            conn = zk.connect()
            # get all attendance logs from device from last sync time 
            attendances = conn.get_attendance()
            conn.disconnect()

            # Insert logs into ERPNextbe
            for att in attendances:
                frappe.get_doc({
                    "doctype": "ZKTeco Attendance Log",
                    "device": dev.name,
                    "employee_id": att.user_id,
                    "timestamp": att.timestamp,
                    "status": att.status
                }).insert(ignore_permissions=True)

            # Update last_sync timestamp
            frappe.db.set_value("ZKTeco Device", dev.name, "last_sync", datetime.now())
            total_logs += len(attendances)

            frappe.logger().info(f"Downloaded {len(attendances)} logs from {dev.name}")

        except Exception as e:
            frappe.log_error(f"ZKTeco Error for {dev.name}: {str(e)}", "ZKTeco Log Download")

    frappe.msgprint(f"Downloaded {total_logs} logs from {len(devices)} devices.")
    return f"Downloaded {total_logs} logs from {len(devices)} devices."