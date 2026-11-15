import sys
import paramiko

from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QGroupBox,
)


# ==========================================
# SSH WORKER
# ==========================================

class SSHWorker(QThread):
    message_received = pyqtSignal(str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.ssh = None
        self.stdin = None
        self.stdout = None
        self.running = True

    def run(self):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(
                paramiko.AutoAddPolicy()
            )

            self.ssh.connect(
                "35.9.42.197",
                username="ece489",
                port=22,
                # Configure SSH authentication here.
            )

            self.stdin, self.stdout, stderr = (
                self.ssh.exec_command(
                    "python3 -u "
                    "/home/ece489/ece480fall2026/demo2/"
                    "motor_controller.py"
                )
            )

            self.connected.emit()

            for line in self.stdout:
                if not self.running:
                    break

                self.message_received.emit(line.strip())

        except Exception as e:
            self.message_received.emit(f"SSH ERROR: {e}")

        finally:
            self.running = False

            if self.ssh:
                self.ssh.close()

            self.disconnected.emit()

    def send_command(self, command):
        if self.stdin and self.running:
            try:
                self.stdin.write(command + "\n")
                self.stdin.flush()
            except Exception as e:
                self.message_received.emit(
                    f"SEND ERROR: {e}"
                )

    def stop(self):
        self.running = False

        if self.stdin:
            try:
                self.stdin.write("STOP\nQUIT\n")
                self.stdin.flush()
            except Exception:
                pass

        if self.ssh:
            self.ssh.close()


# ==========================================
# MAIN GUI
# ==========================================

class MotorControlWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Project Sundial Control Panel")
        self.resize(650, 600)

        self.ssh_worker = SSHWorker()

        self.ssh_worker.message_received.connect(
            self.handle_message
        )

        self.ssh_worker.connected.connect(
            self.on_connected
        )

        self.ssh_worker.disconnected.connect(
            self.on_disconnected
        )

        self.setup_ui()

        self.ssh_worker.start()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        # Connection status
        self.connection_label = QLabel("Connecting...")
        layout.addWidget(self.connection_label)

        # ==================================
        # MOTOR CONTROLS
        # ==================================

        motor_group = QGroupBox("NEMA 23 Linear Motor")
        motor_layout = QHBoxLayout()

        self.forward_button = QPushButton("Forward")
        self.backward_button = QPushButton("Backward")
        self.stop_button = QPushButton("STOP")

        self.forward_button.setEnabled(False)
        self.backward_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        self.forward_button.pressed.connect(
            lambda: self.send_command("FORWARD")
        )

        self.forward_button.released.connect(
            lambda: self.send_command("STOP")
        )

        self.backward_button.pressed.connect(
            lambda: self.send_command("BACKWARD")
        )

        self.backward_button.released.connect(
            lambda: self.send_command("STOP")
        )

        self.stop_button.clicked.connect(
            lambda: self.send_command("STOP")
        )

        motor_layout.addWidget(self.forward_button)
        motor_layout.addWidget(self.backward_button)
        motor_layout.addWidget(self.stop_button)

        motor_group.setLayout(motor_layout)
        layout.addWidget(motor_group)

        # ==================================
        # SENSOR STATUS
        # ==================================

        sensor_group = QGroupBox("Sensor Status")
        sensor_layout = QVBoxLayout()

        self.home_label = QLabel("DUT Home: Unknown")
        self.aligned_label = QLabel("DUT Aligned: Unknown")

        self.forward_limit_label = QLabel(
            "Forward Limit: Unknown"
        )

        self.backward_limit_label = QLabel(
            "Backward Limit: Unknown"
        )

        sensor_layout.addWidget(self.home_label)
        sensor_layout.addWidget(self.aligned_label)
        sensor_layout.addWidget(self.forward_limit_label)
        sensor_layout.addWidget(self.backward_limit_label)

        sensor_group.setLayout(sensor_layout)
        layout.addWidget(sensor_group)

        # ==================================
        # ACTIVITY LOG
        # ==================================

        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        log_layout.addWidget(self.log)
        log_group.setLayout(log_layout)

        layout.addWidget(log_group)

    # ======================================
    # COMMANDS
    # ======================================

    def send_command(self, command):
        self.log.append(f"PC: {command}")
        self.ssh_worker.send_command(command)

    # ======================================
    # SSH EVENTS
    # ======================================

    def on_connected(self):
        self.connection_label.setText("Connected to Raspberry Pi")

        self.forward_button.setEnabled(True)
        self.backward_button.setEnabled(True)
        self.stop_button.setEnabled(True)

        self.send_command("STATUS")

    def on_disconnected(self):
        self.connection_label.setText("Disconnected")

        self.forward_button.setEnabled(False)
        self.backward_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    # ======================================
    # HANDLE PI MESSAGES
    # ======================================

    def handle_message(self, message):
        self.log.append(f"PI: {message}")

        if message.startswith("STATUS "):
            self.parse_status(message)

    def parse_status(self, message):
        values = {}

        for item in message.split()[1:]:
            if "=" in item:
                key, value = item.split("=", 1)
                values[key] = value

        self.home_label.setText(
            f"DUT Home: {values.get('HOME', 'Unknown')}"
        )

        self.aligned_label.setText(
            f"DUT Aligned: {values.get('DUT_ALIGNED', 'Unknown')}"
        )

        self.forward_limit_label.setText(
            f"Forward Limit: "
            f"{values.get('FORWARD_LIMIT', 'Unknown')}"
        )

        self.backward_limit_label.setText(
            f"Backward Limit: "
            f"{values.get('BACKWARD_LIMIT', 'Unknown')}"
        )

    # ======================================
    # CLEANUP
    # ======================================

    def closeEvent(self, event):
        self.ssh_worker.stop()
        self.ssh_worker.wait(2000)
        event.accept()


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MotorControlWindow()
    window.show()

    sys.exit(app.exec())