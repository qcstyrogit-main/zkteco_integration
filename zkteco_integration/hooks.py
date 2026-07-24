app_name = "zkteco_integration"
app_title = "zkteco_integration"
app_publisher = "aljor"
app_description = "zkteco fingerscan device integration for DTR"
app_email = "aljor@qcstyro.com"
app_license = "mit"

scheduler_events = {
	"cron": {"*/30 * * * *": ["zkteco_integration.zkteco_integration.zk_downloader.fetch_and_insert_attendance_logs"]}
}

after_install = "zkteco_integration.setup.ensure_zkteco_device_fields"
after_migrate = "zkteco_integration.setup.ensure_zkteco_device_fields"
