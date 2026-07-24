import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def ensure_zkteco_device_fields():
	"""Keep fields required by the integration present on legacy custom DocTypes."""
	if not frappe.db.exists("DocType", "ZKTeco Device"):
		return

	create_custom_fields(
		{
			"ZKTeco Device": [
				{
					"fieldname": "device_ip",
					"label": "IP Address",
					"fieldtype": "Data",
					"insert_after": "location",
					"reqd": 1,
					"in_list_view": 1,
					"in_standard_filter": 1,
					"description": "IPv4 address or hostname of the ZKTeco device.",
				}
			]
		}
	)
