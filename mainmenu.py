import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QGroupBox,
    QPushButton, QMainWindow, QLabel, QLineEdit,
    QHBoxLayout, QFrame, QSplitter, QTextEdit
)
from PyQt6.QtCore import Qt
from workers import ConnectWorker

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

import math

from PyQt6.QtWidgets import QWidget, QPushButton, QButtonGroup
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor

class EntryLine(QWidget):
    def __init__(
        self,
        prompt="Enter Something:",
        default_value="default value"
    ):
        super().__init__()

        layout = QHBoxLayout(self)

        self.label = QLabel(prompt)
        self.entry = QLineEdit(str(default_value))

        layout.addWidget(self.label)
        layout.addWidget(self.entry)

    def text(self):
        return self.entry.text()


class InfoBox(QGroupBox):
    def __init__(
        self,
        title="Group Box Example",
        description="Description Text",
        button_text="Button Text"
    ):
        super().__init__(title)

        self.setStyleSheet("""
            QGroupBox {
                font-size: 17px;
                font-weight: medium;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
            }
        """)

        self.description = description
        self.button_text = button_text

        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)

        description_label = QLabel(self.description)

        # Store button so we can connect signals later
        self.button = QPushButton(self.button_text)

        self.main_layout.addWidget(description_label, 2)

        self.entry_boxes = QVBoxLayout()
        self.main_layout.addLayout(self.entry_boxes, 7)

        self.main_layout.addWidget(self.button, 1)

    def add_item(self, widget):
        self.entry_boxes.addWidget(widget)

    # NEW: Allow adding layouts as well
    def add_layout(self, layout):
        self.entry_boxes.addLayout(layout)


class DUTSelector(QWidget):

    positionSelected = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        self.setMinimumSize(250, 250)

        self.buttons = []

        # Only one position selected at a time
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(False)

        # Create 12 buttons
        for i in range(12):
            button = QPushButton(str(i + 1), self)

            button.setFixedSize(36, 36)
            button.setCheckable(True)

            button.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border-radius: 18px;
                    font-weight: bold;
                }

                QPushButton:checked {
                    background-color: #27ae60;
                }
            """)

            self.buttons.append(button)
            self.button_group.addButton(button, i + 1)

        # Emit the position number when clicked
        self.button_group.idClicked.connect(
            self.positionSelected.emit
        )

        self.position_buttons()

    def position_buttons(self):
        """Arrange 12 buttons in a circle."""

        center_x = self.width() / 2
        center_y = self.height() / 2

        radius = min(self.width(), self.height()) * 0.35

        for i, button in enumerate(self.buttons):

            angle = -math.pi / 2 + i * (2 * math.pi / 12)

            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)

            # Center button on calculated position
            button.move(
                int(x - button.width() / 2),
                int(y - button.height() / 2)
            )

    def resizeEvent(self, event):
        """Reposition buttons when resized."""

        self.position_buttons()
        super().resizeEvent(event)

    def paintEvent(self, event):
        """Draw the circular DUT board."""

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() / 2
        center_y = self.height() / 2

        radius = min(self.width(), self.height()) * 0.46

        # Main DUT circle
        painter.setPen(QPen(QColor("#34495e"), 3))
        painter.setBrush(QColor("#d6eaf8"))

        painter.drawEllipse(
            QPointF(center_x, center_y),
            radius,
            radius
        )

        # Center circle
        painter.setBrush(QColor("#a9cce3"))
        painter.drawEllipse(
            QPointF(center_x, center_y),
            25,
            25
        )

        # Center label
        painter.setPen(QColor("#2c3e50"))
        painter.drawText(
            QRectF(center_x - 30, center_y - 15, 60, 30),
            Qt.AlignmentFlag.AlignCenter,
            "DUT"
        )

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Project Sundial Control Panel")
        self.header_text = QLabel("PROJECT SUNDIAL")

        self.setGeometry(100, 100, 1000, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # RASPBERRY PI CONNECTION
        self.ssh = None
        self.ip_address = None
        self.username = None
        self.password = None
        self.ssh_port = None

        # MOTOR CONNECTIONS
        self.nema_23_controller = None
        self.nema_17_controller = None

        @property
        def motors(self):
            return self.nema_23_controller is not None and self.nema_17_controller is not None
        
        self.init_ui()

        self.setStyleSheet("""
            QMainWindow {
                background-color: #2C2C2C;
            }

            QWidget {
                color: white;
            }

            QGroupBox {
                background-color: #353535;
                border: 2px solid #555555;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
            }

            QPushButton {
                background-color: #454545;
                color: white;
                border-radius: 5px;
                padding: 8px;
            }
                
            QLineEdit {
                background-color: #FFFFFF;
                color: #34495E;
            }
        """)

    def init_ui(self):
        self.layout = QVBoxLayout(self.central_widget)

        # ====================================
        # HEADER WITH TITLE AND SHOW/HIDE LOG
        # ====================================
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet("""
            .QFrame {
                background-color: #2c3e50;
                border: 2px solid #34495e;
                border-radius: 8px;
            }
        """)
        self.frame_layout = QHBoxLayout(self.header_frame)
        self.header_text = QLabel("PROJECT SUNDIAL")
        self.subheader_text = QLabel("Automated Single Event Effects Testing")

        self.header_text.setStyleSheet("""
            font-size: 30px;
            font-weight: demibold;
            color: white;
        """)

        self.subheader_text = QLabel("Automated Single Event Effects Testing")

        self.subheader_text.setStyleSheet("""
            font-size: 14px;
            color: #bdc3c7;
        """)
        
        self.toggle_log = QPushButton("Show Log")
        self.test_motors = QPushButton("Test Motors")
        self.toggle_log.clicked.connect(self.show_hide_log)
        self.title_layout = QVBoxLayout()
        self.title_layout.addWidget(self.header_text)
        self.title_layout.addWidget(self.subheader_text)
        self.frame_layout.addLayout(self.title_layout, 10)
        self.frame_layout.addWidget(self.test_motors, 1)
        self.frame_layout.addWidget(self.toggle_log, 1)
        self.layout.addWidget(self.header_frame, 1)

        # HORIZONTAL LAYOUT FOR THE BOXES
        self.infoboxes_layout = QHBoxLayout()

        # ====================================
        # 1. CONNECT RASPBERRY PI BOX
        # ====================================

        self.connect_RP = InfoBox(
            "1. Connect Pi",
            "Enter Raspberry Pi connection information",
            "Connect"
        )

        self.ip_address_box = EntryLine(
            prompt="IP Address:",
            default_value="35.9.42.197"
        )

        self.username_box = EntryLine(
            prompt="Username:",
            default_value="ece489"
        )

        self.password_box = EntryLine(
            prompt="Password:",
            default_value="Sundial"
        )

        self.ssh_port_box = EntryLine(
            prompt="SSH Port:",
            default_value=22
        )

        self.connect_RP.add_item(self.ip_address_box)
        self.connect_RP.add_item(self.username_box)
        self.connect_RP.add_item(self.password_box)
        self.connect_RP.add_item(self.ssh_port_box)

        self.rp_connect_button = self.connect_RP.button
        self.rp_connect_button.clicked.connect(self.connect_rp_function)
        self.infoboxes_layout.addWidget(self.connect_RP, 1)

        # ====================================
        # 2. INITIALIZE MOTORS BOX
        # ====================================

        self.motor_pin_setup = InfoBox(
            "2. Initialize Motors",
            "Configure Raspberry Pi GPIO connections",
            "Set Pins"
        )

        # NEMA 23
        self.nema23_info = QGroupBox("NEMA 23 Connections")

        self.en_23 = EntryLine("EN Pin:", "??")
        self.dir_23 = EntryLine("DIR Pin:", "??")
        self.step_23 = EntryLine("STEP Pin:", "??")

        self.nema23_layout = QVBoxLayout(self.nema23_info)

        self.nema23_layout.addWidget(self.en_23)
        self.nema23_layout.addWidget(self.dir_23)
        self.nema23_layout.addWidget(self.step_23)

        # NEMA 17
        self.nema17_info = QGroupBox("NEMA 17 Connections")

        self.en_17 = EntryLine("EN Pin:", 12)
        self.dir_17 = EntryLine("DIR Pin:", 20)
        self.step_17 = EntryLine("STEP Pin:", 21)

        self.M0_17 = EntryLine("M0:", 14)
        self.M1_17 = EntryLine("M1:", 15)
        self.M2_17 = EntryLine("M2:", 18)

        self.nema17_layout = QHBoxLayout(self.nema17_info)

        self.nema17_general_params_layout = QVBoxLayout()
        self.nema17_microstepping_layout = QVBoxLayout()

        self.nema17_general_params_layout.addWidget(self.en_17)
        self.nema17_general_params_layout.addWidget(self.dir_17)
        self.nema17_general_params_layout.addWidget(self.step_17)

        self.nema17_microstepping_layout.addWidget(self.M0_17)
        self.nema17_microstepping_layout.addWidget(self.M1_17)
        self.nema17_microstepping_layout.addWidget(self.M2_17)

        self.nema17_layout.addLayout(self.nema17_general_params_layout)
        self.nema17_layout.addLayout(self.nema17_microstepping_layout)

        # Put both motors side by side
        self.motor_info = QHBoxLayout()

        self.motor_info.addWidget(self.nema23_info)
        self.motor_info.addWidget(self.nema17_info)

        # Add motor layout into InfoBox
        self.motor_pin_setup.add_layout(self.motor_info)

        self.infoboxes_layout.addWidget(self.motor_pin_setup, 1)

        # ====================================
        # 3. TESTING PARAMETERS BOX
        # ====================================

        self.testing_setup = InfoBox(
            "3. Enter Testing Parameters",
            "Configure testing settings",
            "Enter"
        )

        self.dut_selector = DUTSelector()
        self.testing_setup.add_item(self.dut_selector)

        self.infoboxes_layout.addWidget(self.testing_setup, 1)

        # Create a widget to hold all 3 InfoBoxes
        self.infoboxes_container = QWidget()
        self.infoboxes_container.setLayout(self.infoboxes_layout)

        # Create vertical splitter
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.layout.addWidget(self.splitter, 6)

        # Top section: InfoBoxes
        self.splitter.addWidget(self.infoboxes_container)

        # Bottom section: Log
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Log outputs will appear here...")
        self.log_output.setStyleSheet("""
            background-color: #353535;
            color: white;
            border: 2px solid #444444;
            border-radius: 5px;
        """)

        self.splitter.addWidget(self.log_output)

        # Default sizes
        self.splitter.setSizes([450, 200])

        # Hide log initially
        self.log_output.show() 

    def connect_rp_function(self):

        self.log("Attempting connection to Raspberry Pi", "info")
        ip = self.ip_address_box.text().strip()
        username = self.username_box.text().strip()
        password = self.password_box.text()
        port_text = self.ssh_port_box.text().strip()

        if not (ip and username and password and port_text):
            self.log("Please input all parameters", "warning")
            return

        try:
            port = int(port_text)
            if not 1 <= port <= 65535:
                raise ValueError()
        except ValueError:
            self.log("Invalid port", "error")
            return

        self.log("Connecting to Raspberry Pi...")

        self.worker = ConnectWorker(ip, port, username, password)

        self.worker.success.connect(self.connection_success)
        self.worker.error.connect(self.connection_error)
        self.worker.finished.connect(
            lambda: self.rp_connect_button.setEnabled(True)
        )

        self.rp_connect_button.setEnabled(False)
        self.worker.start()

    def connection_success(self, ssh):
        if self.ssh is not None:
            self.ssh.close()
        self.ssh = ssh
        self.log("Successfully connected!", "success")

    def connection_error(self, message):
        self.log(f"Connection failed: {message}", "error")

    def show_hide_log(self):
        # Toggles the visibility of the log output widget.
        if self.log_output.isVisible():
            self.log_output.hide()
            self.toggle_log.setText("Show Log")
        else:
            self.log_output.show()
            self.toggle_log.setText("Hide Log")
            self.splitter.setSizes([450, 200])

    def log(self, message, level="info"):
        colors = {
            "info": "#FFFFFF",
            "success": "#4CAF50",
            "warning": "#FFC107",
            "error": "#F44336"
        }

        color = colors.get(level, "#FFFFFF")

        self.log_output.append(
            f'<span style="color: {color};">{message}</span>'
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())