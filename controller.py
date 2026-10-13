import paramiko
from PyQt6.QtCore import QThread, pyqtSignal
import time

class ControlWorker(QThread):
    progress = pyqtSignal(str)
    success = pyqtSignal(str)
    def __init__(self, controller, command=None):
        super().__init__()
        self.controller = controller
        self.command = command

    def run(self):
        self.progress.emit("Attempting to connect RP")

        try:
            self.controller.connect_RP()
        except Exception as e:
            self.progress.emit(f"Error executing command '{self.command}': {e}")
            self.success.emit("Failed to connect to Raspberry Pi")
            return
        self.progress.emit("Successfully connected to Raspberry Pi")

class Controller:
    # Get information from the user about the Raspberry Pi connection through input
    # Pass info into controller object
    def __init__(self, ip="35.12.217.8", username = "ece489", password = "Sundial"):
        self.ip = ip
        self.username = username
        self.password = password
        self.ssh_client = None

        self.RP_connected = False
        self.motors_connected = False
        self.DUT_geometry = False
        self.device_locations = False
        self.ready = self.system_ready()

    def system_ready(self):
        return self.RP_connected and self.motors_connected and self.DUT_geometry and self.device_locations

    def connect_RP(self):
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(self.ip, username=self.username, password=self.password)
            print(f"Connected to Raspberry Pi at {self.ip} via SSH")
        except Exception as e:
            print(f"Error connecting to Raspberry Pi: {e}")

    def disconnect_RP(self):
        if self.ssh_client:
            self.ssh_client.close()
            print("Disconnected from Raspberry Pi")
        else:
            print("No active connection to disconnect.")

    def execute(self, command):
        pass