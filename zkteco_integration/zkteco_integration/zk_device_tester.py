import frappe
from zk import ZK, const
from datetime import datetime

class ZKDeviceTester:
    def __init__(self, ip_address, port=4370,password=None):
        self.ip_address = ip_address
        self.port = int(port)
        self.password = "0"
        self.zk = ZK(ip_address, port=self.port, timeout=5, password=self.password)
        
    def test_connection(self):
        """Test basic connection to the device"""
        try:
            conn = self.zk.connect()
            if conn:
                print(f"✓ Successfully connected to device at {self.ip_address}:{self.port}")
                firmware_version = self.get_firmware_version(conn)
                print(f"  - Firmware Version: {firmware_version}")
                serial_number = self.get_serial_number(conn)
                print(f"  - Serial Number: {serial_number}")
                conn.disconnect()
                return True
        except Exception as e:
            print(f"✗ Connection failed: {str(e)}")
            return False

    def get_firmware_version(self, conn):
        """Get device firmware version"""
        try:
            return conn.get_firmware_version()
        except:
            return "Unknown"

    def get_serial_number(self, conn):
        """Get device serial number"""
        try:
            return conn.get_serialnumber()
        except:
            return "Unknown"

    def get_device_info(self):
        """Get detailed device information"""
        try:
            conn = self.zk.connect()
            if conn:
                info = {
                    'firmware_version': self.get_firmware_version(conn),
                    'serial_number': self.get_serial_number(conn),
                    'platform': conn.get_platform(),
                    'device_name': conn.get_device_name(),
                    'users': len(conn.get_users()),
                    'fingerprints': len(conn.get_templates()),
                }
                conn.disconnect()
                return info
        except Exception as e:
            print(f"Error getting device info: {str(e)}")
            return None

    def get_all_users(self):
        """Get list of all users registered in the device"""
        try:
            conn = self.zk.connect()
            if conn:
                users = conn.get_users()
                conn.disconnect()
                return users
        except Exception as e:
            print(f"Error getting users: {str(e)}")
            return []

    def get_attendance_logs(self, limit=None):
        """
        Get all attendance logs from the device.
        Args:
            limit: Optional maximum number of logs to retrieve
        Returns:
            List of attendance records (optionally limited)
        """
        try:
            conn = self.zk.connect()
            if conn:
                attendances = conn.get_attendance()
                conn.disconnect()
                logs = list(attendances)
                if limit:
                    logs = logs[:limit]
                return logs
        except Exception as e:
            print(f"Error getting attendance logs: {str(e)}")
            return []

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

def get_test_device():
    """Helper function to get the first active device from the database"""
    device = frappe.get_all(
        "ZKTeco Device",
        filters={"status": "Active"},
        fields=["name", "device_ip", "port"],
        limit=1
    )
    if device:
        return device[0]
    return None

# Example usage in bench console:
"""
# Import the tester
from zkteco_integration.zkteco_integration.utils.zk_device_tester import ZKDeviceTester

# Get first active device from database
from zkteco_integration.zkteco_integration.utils.zk_device_tester import get_test_device
device = get_test_device()

# Create tester instance
tester = ZKDeviceTester(device.device_ip, device.port)

# Test connection
tester.test_connection()

# Get device info
info = tester.get_device_info()
print("Device Info:", info)

# Get users
users = tester.get_all_users()
print("Users:", users)

"""
"""
# Example usage in bench console:
from zkteco_integration.zkteco_integration.utils.zk_device_tester import ZKDeviceTester, get_test_device

# Get first active device from database
device = get_test_device()
tester = ZKDeviceTester(device.device_ip, device.port)

# Test connection
tester.test_connection()

# Get device info
info = tester.get_device_info()
print("Device Info:", info)

# Get users
users = tester.get_all_users()
print("Users:", users)

# Get last 5 attendance logs
logs = tester.get_attendance_logs(limit=5)
print("Recent Logs:", logs)

# Get only new logs after a certain timestamp
from datetime import datetime, timedelta
last_time = datetime.now() - timedelta(days=1)  # Example: logs after yesterday
new_logs = tester.get_new_attendance_logs(last_time)
print("New Logs after", last_time, ":", new_logs)

# Get logs in a date range
start = datetime(2024, 10, 1, 0, 0, 0)
end = datetime(2024, 10, 2, 23, 59, 59)
range_logs = tester.get_attendance_logs_by_range(start, end)
print(f"Logs from {start} to {end}:", range_logs)
"""