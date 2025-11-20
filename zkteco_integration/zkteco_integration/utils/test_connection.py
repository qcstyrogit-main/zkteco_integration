from pyzatt.pyzatt import ZKSS

# --- Device Connection Details ---
# Replace with your device's IP address and port
DEVICE_IP = "192.168.1.64"  # Example IP
DEVICE_PORT = 5005

def test_device_connection(ip, port):
    """
    Tests the connection to a ZK Teco device.
    """
    # 1. Create an instance of the ZKSS class
    zk = ZKSS()

    print(f"Attempting to connect to device at {ip}:{port}...")

    try:
        # 2. Call the connect_net method
        is_connected = zk.connect_net(ip, port)

        # 3. Check the result
        if is_connected:
            print("✅ Connection Successful!")
            
            # You can now get more information from the device
            firmware = zk.get_firmware_version()
            serial_number = zk.get_serial_number()
            
            print(f"   - Firmware Version: {firmware}")
            print(f"   - Serial Number: {serial_number}")

            # 4. Always disconnect when you are done
            zk.disconnect()
            print("🔌 Disconnected successfully.")
        else:
            print("❌ Connection Failed: The device did not acknowledge the connection request.")

    except Exception as e:
        print(f"❌ An error occurred during connection: {e}")
        # Ensure the socket is closed on error if it was created
        if hasattr(zk, 'soc_zk'):
            zk.soc_zk.close()

# --- Run the test ---
if __name__ == "__main__":
    test_device_connection(DEVICE_IP, DEVICE_PORT)

