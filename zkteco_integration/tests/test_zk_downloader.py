import unittest
from unittest.mock import patch, MagicMock

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from zkteco_integration.zkteco_integration.zk_downloader import fetch_and_insert_attendance_logs

class TestZKDownloader(unittest.TestCase):
    @patch('zkteco_integration.zkteco_integration.zk_downloader.ZK')
    @patch('zkteco_integration.zkteco_integration.zk_downloader.frappe')
    #@patch('zkteco_integration.zkteco_integration.zk_downloader.clean_duplicate_logs')
    @patch('zkteco_integration.zkteco_integration.zk_downloader.check_existing_checkin')
    def test_fetch_and_insert_attendance_logs(self, mock_check_existing, mock_clean_dupes, mock_frappe, mock_ZK):
        # Setup device as MagicMock with attributes
        device = MagicMock()
        device.name = 'TestDevice'
        device.device_ip = '192.168.1.201'
        device.port = 4370
        device.machine_no = 'M01'
        device.last_sync = datetime(2025, 10, 20, 0, 0, 0)
        device.device_id = 'D01'
        mock_frappe.get_all.return_value = [device]
        # Setup attendance log
        log = MagicMock()
        log.user_id = '123'
        log.timestamp = datetime(2025, 10, 21, 8, 0, 0)
        # ZK mock
        mock_conn = MagicMock()
        mock_conn.get_attendance.return_value = [log]
        mock_ZK.return_value.connect.return_value = mock_conn
         
        # No duplicate checkin
        mock_check_existing.return_value = False
        # Employee exists
        mock_frappe.db.get_value.return_value = 'EMP-001'
        # Employee doc
        emp_doc = MagicMock()
        emp_doc.shift = None
        def get_doc_side_effect(arg, *args, **kwargs):
            if arg == 'Employee':
                return emp_doc
            if isinstance(arg, dict) and arg.get('doctype') == 'Employee Checkin':
                checkin_doc = MagicMock()
                checkin_doc.insert = MagicMock()
                checkin_doc.fetch_shift = MagicMock()
                return checkin_doc
            return MagicMock()
        mock_frappe.get_doc.side_effect = get_doc_side_effect
        # Run
        fetch_and_insert_attendance_logs()
        # Assertions
        mock_frappe.get_all.assert_called_once()
        mock_ZK.assert_called_with('192.168.1.201', port=4370, timeout=10, password='0')
        mock_conn.get_attendance.assert_called_once()
        mock_clean_dupes.assert_called_once()
        mock_frappe.db.get_value.assert_called_once_with('Employee', {'attendance_device_id': 'M01-123', 'status': 'Active'}, 'name')
        # Should insert checkin
        inserted = False
        for call in mock_frappe.get_doc.mock_calls:
            if isinstance(call[1][0], dict) and call[1][0].get('doctype') == 'Employee Checkin':
                inserted = True
        self.assertTrue(inserted)

if __name__ == '__main__':
    unittest.main()