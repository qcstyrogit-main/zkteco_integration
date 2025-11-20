import frappe
from frappe.model.document import Document
from zk import ZK, const
from datetime import datetime

class ZKTecoLogDownloader(Document):

    @frappe.whitelist()
    def download_all_logs(self):
        devices = frappe.get_all("ZKTeco Device", filters={"status": "Active"}, fields=["name", "device_ip", "port"])
        total_logs = 0

        for dev in devices:
            frappe.msgprint(f"Connecting to device {dev.name} ({dev.device_ip})...")
            try:
                zk = ZK(dev.device_ip, port=int(dev.port or 4370), timeout=5)
                conn = zk.connect()
                attendances = conn.get_attendance()
                conn.disconnect()

                for att in attendances:
                    frappe.get_doc({
                        "doctype": "ZKTeco Attendance Log",
                        "device": dev.name,
                        "employee_id": att.user_id,
                        "timestamp": att.timestamp,
                        "status": att.status
                    }).insert(ignore_permissions=True)

                frappe.db.set_value("ZKTeco Device", dev.name, "last_sync", datetime.now())
                total_logs += len(attendances)

            except Exception as e:
                frappe.log_error(f"ZKTeco Error for {dev.name}: {str(e)}")

        frappe.msgprint(f"Downloaded {total_logs} logs from {len(devices)} devices.")



        