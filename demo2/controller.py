import sys
import threading
import queue
import paramiko
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QGroupBox,
                             QTextEdit, QLineEdit, QComboBox, QSpinBox)

HOST = '35.9.42.197'
USERNAME = 'ece489'
PASSWORD = 'Sundial'  # Prefer an SSH key or environment variable for a real deployment.
REMOTE_SCRIPT = '/home/ece489/ece480fall2026/demo2/motor_controller.py'


class SSHWorker(QThread):
    received = pyqtSignal(str)
    connection_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.commands = queue.Queue()
        self.closing = threading.Event()
        self.ssh = None

    def send(self, command):
        if not self.closing.is_set():
            self.commands.put(command)

    def stop(self):
        self.closing.set()
        self.commands.put('STOP ALL')
        self.commands.put('QUIT')

    def run(self):
        ssh = paramiko.SSHClient()
        self.ssh = ssh
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(HOST, username=USERNAME, password=PASSWORD, port=22,
                        timeout=8, auth_timeout=8)
            stdin, stdout, stderr = ssh.exec_command(f'python3 -u {REMOTE_SCRIPT}')
            channel = stdout.channel
            self.connection_changed.emit(True)
            self.received.emit('CONNECTED')
            channel.settimeout(0.1)
            pending = ''
            while True:
                try:
                    while True:
                        command = self.commands.get_nowait()
                        stdin.write(command + '\n')
                        stdin.flush()
                except queue.Empty:
                    pass
                if channel.recv_ready():
                    data = channel.recv(4096).decode('utf-8', errors='replace')
                    pending += data
                    while '\n' in pending:
                        line, pending = pending.split('\n', 1)
                        self.received.emit(line.rstrip('\r'))
                if channel.recv_stderr_ready():
                    error = channel.recv_stderr(4096).decode('utf-8', errors='replace')
                    self.received.emit('STDERR: ' + error.strip())
                if channel.exit_status_ready():
                    if pending.strip():
                        self.received.emit(pending.strip())
                    break
                if self.closing.is_set() and self.commands.empty():
                    # Give the Pi a brief chance to process STOP/QUIT.
                    channel.shutdown_write()
                    break
                self.msleep(20)
        except Exception as exc:
            self.received.emit(f'SSH ERROR: {exc}')
        finally:
            ssh.close()
            self.connection_changed.emit(False)


class ControlWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Project Sundial Motor Control')
        self.resize(650, 650)
        self.worker = SSHWorker()
        self.worker.received.connect(self.handle_message)
        self.worker.connection_changed.connect(self.set_connected)
        self.connected = False
        self.controls = []
        self.labels = {}
        self.setup_ui()
        self.worker.start()

    def setup_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        self.connection_label = QLabel('Connecting...')
        layout.addWidget(self.connection_label)
        for motor, name in [('23', 'NEMA 23 — Linear'), ('17', 'NEMA 17 — Rotary')]:
            group = QGroupBox(name)
            inner = QVBoxLayout(group)
            manual = QHBoxLayout()
            for label, direction in [('Forward / CW', 'FORWARD'), ('Backward / CCW', 'BACKWARD')]:
                button = QPushButton(label + ' (hold)')
                button.pressed.connect(lambda m=motor, d=direction: self.send(f'MOVE {m} {d}'))
                button.released.connect(lambda m=motor: self.send(f'STOP {m}'))
                manual.addWidget(button)
                self.controls.append(button)
            inner.addLayout(manual)
            fixed = QHBoxLayout()
            direction_box = QComboBox()
            direction_box.addItems(['FORWARD', 'BACKWARD'])
            count = QSpinBox()
            count.setRange(1, 1_000_000)
            count.setValue(100)
            go = QPushButton('Move steps')
            go.clicked.connect(lambda checked=False, m=motor, d=direction_box, n=count:
                               self.send(f'MOVE {m} {d.currentText()} {n.value()}'))
            stop = QPushButton('STOP')
            stop.clicked.connect(lambda checked=False, m=motor: self.send(f'STOP {m}'))
            fixed.addWidget(direction_box)
            fixed.addWidget(count)
            fixed.addWidget(go)
            fixed.addWidget(stop)
            inner.addLayout(fixed)
            self.controls.extend([direction_box, count, go, stop])
            layout.addWidget(group)
        stop_all = QPushButton('STOP ALL')
        stop_all.clicked.connect(lambda: self.send('STOP ALL'))
        layout.addWidget(stop_all)
        self.controls.append(stop_all)
        status = QGroupBox('Sensors / Status')
        status_layout = QVBoxLayout(status)
        for key in ('SENSOR7', 'SENSOR8', 'HOME', 'DUT_ALIGNED',
                    'FORWARD_LIMIT', 'BACKWARD_LIMIT', 'MOVING17', 'MOVING23',
                    'REMAINING17', 'REMAINING23'):
            label = QLabel(f'{key}: Unknown')
            self.labels[key] = label
            status_layout.addWidget(label)
        layout.addWidget(status)
        refresh = QPushButton('Refresh status')
        refresh.clicked.connect(lambda: self.send('STATUS'))
        layout.addWidget(refresh)
        self.controls.append(refresh)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        self.set_connected(False)

    def set_connected(self, connected):
        self.connected = connected
        self.connection_label.setText('Connected' if connected else 'Disconnected')
        for control in self.controls:
            control.setEnabled(connected)
        if connected:
            self.send('STATUS')

    def send(self, command):
        if self.connected:
            self.worker.send(command)
            if command != 'STATUS':
                self.log.append('PC: ' + command)

    def handle_message(self, message):
        self.log.append('PI: ' + message)
        if message.startswith('STATUS '):
            for item in message.split()[1:]:
                if '=' in item:
                    key, value = item.split('=', 1)
                    if key in self.labels:
                        self.labels[key].setText(f'{key}: {value}')

    def closeEvent(self, event):
        self.worker.stop()
        self.worker.wait(2000)
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ControlWindow()
    window.show()
    sys.exit(app.exec())
