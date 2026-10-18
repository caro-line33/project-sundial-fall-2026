from PyQt6.QtCore import QThread, pyqtSignal
import paramiko

class ConnectWorker(QThread):
    success = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, ip, port, username, password):
        super().__init__()
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password

    def run(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(
                hostname=self.ip,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=5
            )

            self.success.emit(ssh)

        except Exception as e:
            ssh.close()
            self.error.emit(str(e))

class MotorWorker(QThread):
    success = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, controller, motor, steps, direction):
        super().__init__()

        self.controller = controller
        self.motor = motor
        self.steps = steps
        self.direction = direction

    def run(self):
        try:
            result = self.controller.move_motor(
                self.motor,
                self.steps,
                self.direction
            )
            self.success.emit(result)

        except Exception as e:
            self.error.emit(str(e))