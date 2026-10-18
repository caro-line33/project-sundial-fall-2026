import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QGroupBox,
    QPushButton, QMainWindow, QLabel, QLineEdit,
    QHBoxLayout, QFrame, QSplitter, QTextEdit, QComboBox
)
from PyQt6.QtCore import Qt, QEvent
from workers import ConnectWorker
import json
import math
from html import escape

from PyQt6.QtWidgets import QWidget, QPushButton, QButtonGroup
from PyQt6.QtCore import pyqtSignal, QPointF, QRectF
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
    """One step of the setup wizard, with an explicit available/locked label."""

    def __init__(
        self,
        title="Group Box Example",
        description="Description Text",
        button_text="Button Text"
    ):
        super().__init__(title)
        self.setObjectName("stepBox")
        self.description = description
        self.button_text = button_text
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)

        description_row = QHBoxLayout()
        self.description_label = QLabel(self.description)
        self.description_label.setObjectName("stepDescription")
        # self.status_label = QLabel("AVAILABLE")
        # self.status_label.setObjectName("sectionStatus")
        description_row.addWidget(self.description_label, 1)
        # description_row.addWidget(self.status_label)

        self.button = QPushButton(self.button_text)
        self.main_layout.addLayout(description_row, 2)

        self.entry_boxes = QVBoxLayout()
        self.main_layout.addLayout(self.entry_boxes, 7)
        self.main_layout.addWidget(self.button, 1)

    # def changeEvent(self, event):
    #    super().changeEvent(event)
    #    if event.type() == QEvent.Type.EnabledChange and hasattr(self, "status_label"):
    #        self.status_label.setText("AVAILABLE" if self.isEnabled() else "LOCKED")

    def add_item(self, widget):
        self.entry_boxes.addWidget(widget)

    def add_layout(self, layout):
        self.entry_boxes.addLayout(layout)


class DUTSelector(QWidget):

    positionSelected = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        self.setMinimumSize(250, 250)

        self.buttons = []
        self.draw_colors = {
            "border": "#385775", "board": "#DCE8F4",
            "hub": "#B7CFE6", "text": "#213E5A",
            "disabled_border": "#A9B8C8", "disabled_board": "#D6DEE7",
            "disabled_hub": "#BBC7D4", "disabled_text": "#8A9BAB",
        }

        # Only one position selected at a time
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(False)

        # Create 12 buttons
        for i in range(12):
            button = QPushButton(str(i + 1), self)

            button.setFixedSize(36, 36)
            button.setCheckable(True)

            button.setObjectName("dutPosition")

            self.buttons.append(button)
            self.button_group.addButton(button, i + 1)

        # Emit the position number when clicked
        self.button_group.idClicked.connect(
            self.positionSelected.emit
        )

        self.position_buttons()

    def set_draw_colors(self, colors):
        self.draw_colors = colors
        self.update()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.EnabledChange:
            self.update()

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

        # Use faded colors when the testing section is locked.
        disabled = not self.isEnabled()
        border_color = self.draw_colors["disabled_border" if disabled else "border"]
        board_color = self.draw_colors["disabled_board" if disabled else "board"]
        hub_color = self.draw_colors["disabled_hub" if disabled else "hub"]
        label_color = self.draw_colors["disabled_text" if disabled else "text"]

        painter.setPen(QPen(QColor(border_color), 3))
        painter.setBrush(QColor(board_color))

        painter.drawEllipse(
            QPointF(center_x, center_y),
            radius,
            radius
        )

        # Center circle
        painter.setBrush(QColor(hub_color))
        painter.drawEllipse(
            QPointF(center_x, center_y),
            25,
            25
        )

        # Center label
        painter.setPen(QColor(label_color))
        painter.drawText(
            QRectF(center_x - 30, center_y - 15, 60, 30),
            Qt.AlignmentFlag.AlignCenter,
            "DUT"
        )

class MotorTestWindow(QWidget):
    def __init__(self, ssh):
        super().__init__()
        self.ssh = ssh
        self.setWindowTitle("Motor Test Window")
        self.setGeometry(150, 150, 400, 300)

        layout = QHBoxLayout()

        self.read_motor_params()

        # NEMA 17 STUFF
        self.nema17_microstep_mode = 1
        self.nema17_direction = 1

        self.nema17_info = InfoBox(title="Nema 17", description="Motor Movement Parameters for Nema 17 (Rotation)", button_text="Run Command")
        self.nema17_number_of_steps = EntryLine(prompt = "Number of steps", default_value = " ")
        self.nema17_direction_box = QComboBox(self.nema17_info)
        self.nema17_direction_box.addItems(["Clockwise", "Counterclockwise"])
        self.nema17_direction_box.currentIndexChanged.connect(self.update_direction_17)

        self.nema17_microstep = QComboBox(self.nema17_info)
        self.nema17_microstep.addItems(["Full Step (1.8 deg)", #  index 0
                                        "1/2 Step (0.9 deg)",  # index 1
                                        "1/4 Step (0.45 deg)", # index 2
                                        "1/8 Step (0.225 deg)", # index 3
                                        "1/16 Step (0.1125 deg)", # index 4
                                        "1/32 Step (0.05625 deg)"]) # index 5
        self.nema17_microstep.currentIndexChanged.connect(self.update_microstep_17)
        self.test_nema17_button = self.nema17_info.button
        self.test_nema17_button.clicked.connect(self.test_nema17_motor)

        self.nema17_info.add_item(self.nema17_number_of_steps)
        self.nema17_info.add_item(self.nema17_direction_box)
        self.nema17_info.add_item(self.nema17_microstep)
        layout.addWidget(self.nema17_info)

        self.test_nema23_button = QPushButton("Test NEMA 23 Motor")
        self.test_nema23_button.clicked.connect(self.test_nema23_motor)

        # NEMA 23 STUFF
        self.nema23_direction = 1
        self.nema23_steps = 10

        self.nema23_info = InfoBox(title="Nema 23", description="Motor Movement Parameters for Nema 23 (Linear)", button_text="Run Command")
        self.nema23_number_of_steps = EntryLine(prompt = "Number of steps", default_value = " ")
        self.nema23_direction_box = QComboBox(self.nema23_info)
        self.nema23_direction_box.addItems(["Forwards", "Backwards"])
        self.nema23_direction_box.currentIndexChanged.connect(self.update_direction_23)

        self.nema23_info.add_item(self.nema23_number_of_steps)
        self.nema23_info.add_item(self.nema23_direction_box)
        layout.addWidget(self.nema23_info)
        self.setLayout(layout)

    def read_motor_params(self):
        
    def test_nema17_motor(self):
        pass

    def test_nema23_motor(self):
        pass

    def update_microstep_17(self):
        self.nema17_microstep_mode = 2 ** int(self.nema17_microstep.currentIndex())
        print(self.nema17_microstep_mode)

    def update_direction_17(self):
            self.nema17_direction = int(self.nema17_direction_box.currentIndex())
            print(self.nema17_direction)

    def update_direction_23(self):
        self.nema23_direction = int(self.nema23_direction_box.currentIndex())
        print(self.nema23_direction)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Project Sundial Control Panel")
        self.setGeometry(100, 100, 1000, 700)

        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)

        # RASPBERRY PI CONNECTION
        self.ssh = None
        self.rp_connected = False
        self.ip_address = None
        self.username = None
        self.password = None
        self.ssh_port = None

        # MOTOR CONNECTIONS
        self.nema_23_controller = None
        self.nema_17_controller = None
        
        self.init_ui()

        # Apply AFTER creating the widgets so it covers the whole window.
        self.color_theme = "Dark"
        self.apply_theme()

        self.motor_pins = False

    def apply_theme(self):
        if self.color_theme == "Light":
            theme = "Dark"
        else:
            theme = "Light"

        if theme == "Dark":
            c = {
                "window": "#0F1726", "card": "#1C2A3C", "border": "#587AA0",
                "text": "#F0F5FC", "muted": "#BAC8D8",
                "locked": "#111B29", "locked_border": "#3C4B5F",
                "locked_text": "#7F93AA", "accent": "#2563C9",
                "accent_hover": "#347AE2", "disabled_button": "#29394D",
                "input": "#27384C", "input_border": "#50647C",
                "disabled_input": "#1A2635", "header": "#152B47",
                "header_edge": "#34516F", "header_button": "#284461",
                "log": "#0B1320", "log_border": "#394D64",
                "ready": "#7EE2B0", "placeholder": "#8C9FB2",
                "board": "#304962", "hub": "#405F7B",
                "board_border": "#8CB1D6", "board_text": "#E4F1FF",
                "board_disabled": "#1B2838", "hub_disabled": "#28394B",
                "board_disabled_border": "#44576B", "board_disabled_text": "#70859C",
            }
        else:
            c = {
                "window": "#EDF2F7", "card": "#FFFFFF", "border": "#6089BD",
                "text": "#1D3049", "muted": "#51657C",
                "locked": "#DDE5EE", "locked_border": "#A5B3C4",
                "locked_text": "#687C91", "accent": "#2362BE",
                "accent_hover": "#174E9F", "disabled_button": "#B8C5D3",
                "input": "#F8FAFD", "input_border": "#BCCBDC",
                "disabled_input": "#CAD5E0", "header": "#17324F",
                "header_edge": "#355876", "header_button": "#2F5274",
                "log": "#142237", "log_border": "#405773",
                "ready": "#087C5E", "placeholder": "#70839B",
                "board": "#D8E7F4", "hub": "#B4D0E6",
                "board_border": "#365F8A", "board_text": "#213E5A",
                "board_disabled": "#C8D4DF", "hub_disabled": "#B3C0CC",
                "board_disabled_border": "#9AAAB9", "board_disabled_text": "#8395A5",
            }

        self.setStyleSheet(f"""
            QMainWindow, QWidget#centralWidget {{
                background-color: {c['window']};
            }}
            QWidget#infoboxesContainer {{ background-color: transparent; }}

            QFrame#headerFrame {{
                background-color: {c['header']};
                border: 1px solid {c['header_edge']};
                border-radius: 10px;
            }}
            QLabel#headerTitle {{ color: #FFFFFF; font-size: 29px; font-weight: 700; }}
            QLabel#headerSubtitle {{ color: #C5D5E5; font-size: 13px; }}
            QLabel#themeLabel {{ color: #DCE9F6; font-size: 12px; }}

            QGroupBox {{
                background-color: {c['card']};
                color: {c['text']};
                border: 2px solid {c['border']};
                border-radius: 9px;
                margin-top: 10px;
                padding: 11px;
                font-size: 15px;
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
            }}
            QGroupBox:disabled {{
                background-color: {c['locked']};
                color: {c['locked_text']};
                border: 2px dashed {c['locked_border']};
            }}

            QLabel {{ color: {c['text']}; font-weight: normal; }}
            QLabel#stepDescription {{ color: {c['muted']}; }}
            QLabel#sectionStatus {{ color: {c['ready']}; font-size: 11px; font-weight: 700; }}
            QLabel:disabled, QLabel#stepDescription:disabled,
            QLabel#sectionStatus:disabled {{ color: {c['locked_text']}; }}

            QPushButton {{
                background-color: {c['accent']};
                color: #FFFFFF;
                border: 1px solid {c['accent']};
                border-radius: 6px;
                padding: 8px 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {c['accent_hover']}; }}
            QPushButton:disabled {{
                background-color: {c['disabled_button']};
                border: 1px solid {c['locked_border']};
                color: {c['locked_text']};
            }}
            QPushButton#headerButton {{
                background-color: {c['header_button']};
                border: 1px solid {c['header_edge']};
                color: #FFFFFF;
            }}
            QPushButton#headerButton:hover {{ background-color: {c['accent']}; }}

            QLineEdit {{
                background-color: {c['input']};
                color: {c['text']};
                border: 1px solid {c['input_border']};
                border-radius: 5px;
                padding: 5px 7px;
                selection-background-color: {c['accent']};
            }}
            QLineEdit:disabled {{
                background-color: {c['disabled_input']};
                color: {c['locked_text']};
                border: 1px solid {c['locked_border']};
            }}

            QComboBox {{
                background-color: {c['header_button']};
                color: #FFFFFF;
                border: 1px solid {c['header_edge']};
                border-radius: 6px;
                padding: 6px 14px;
                min-width: 95px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {c['card']};
                color: {c['text']};
                selection-background-color: {c['accent']};
                selection-color: #FFFFFF;
            }}

            QTextEdit#logOutput {{
                background-color: {c['log']};
                color: #F1F5FA;
                border: 1px solid {c['log_border']};
                border-radius: 7px;
                padding: 8px;
                font-family: Consolas, monospace;
                font-size: 12px;
            }}
            QPushButton#dutPosition {{
                background-color: {c['accent']};
                color: #FFFFFF;
                border: 1px solid {c['border']};
                border-radius: 18px;
                padding: 0;
                font-weight: 700;
            }}
            QPushButton#dutPosition:checked {{ background-color: #108A66; }}
            QPushButton#dutPosition:disabled {{
                background-color: {c['disabled_button']};
                border: 1px solid {c['locked_border']};
                color: {c['locked_text']};
            }}
        """)

        # DUTSelector draws its own circles: CSS alone would not recolor them.
        self.dut_selector.set_draw_colors({
            "border": c["board_border"], "board": c["board"],
            "hub": c["hub"], "text": c["board_text"],
            "disabled_border": c["board_disabled_border"],
            "disabled_board": c["board_disabled"],
            "disabled_hub": c["hub_disabled"],
            "disabled_text": c["board_disabled_text"],
        })

        self.color_theme = theme

    def init_ui(self):
        self.layout = QVBoxLayout(self.central_widget)

        # ====================================
        # HEADER WITH TITLE AND SHOW/HIDE LOG
        # ====================================
        self.header_frame = QFrame()
        self.header_frame.setObjectName("headerFrame")
        self.frame_layout = QHBoxLayout(self.header_frame)
        self.header_text = QLabel("PROJECT SUNDIAL")
        self.header_text.setObjectName("headerTitle")
        self.subheader_text = QLabel("Automated Single Event Effects Testing")
        self.subheader_text.setObjectName("headerSubtitle")

        self.toggle_log = QPushButton("Hide Log")
        self.toggle_log.setObjectName("headerButton")
        self.toggle_log.clicked.connect(self.show_hide_log)

        self.theme_select = QPushButton("Switch Color Theme")
        self.theme_select.clicked.connect(self.apply_theme)
        self.title_layout = QVBoxLayout()
        self.title_layout.addWidget(self.header_text)
        self.title_layout.addWidget(self.subheader_text)
        self.frame_layout.addLayout(self.title_layout, 10)

        self.frame_layout.addWidget(self.toggle_log, 1)
        self.frame_layout.addWidget(self.theme_select)
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
            "Test Motors"
        )

        # NEMA 23
        self.nema23_info = QGroupBox("NEMA 23 Connections")

        self.en_23 = EntryLine("EN Pin:", 22)
        self.dir_23 = EntryLine("DIR Pin:", 27)
        self.step_23 = EntryLine("STEP Pin:", 17)

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


        self.set_motor_pin_info_button = QPushButton("Set Pins")
        self.set_motor_pin_info_button.clicked.connect(self.save_motor_pins)

        self.test_motors_button = self.motor_pin_setup.button
        self.test_motors_button.clicked.connect(self.open_motor_test_window)
        self.test_motors_button.setEnabled(self.rp_connected and self.motor_pins)

        # Add motor layout into InfoBox
        self.motor_pin_setup.add_layout(self.motor_info)
        self.motor_pin_setup.add_item(self.set_motor_pin_info_button)
        self.motor_pin_setup.setEnabled(self.rp_connected)
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
        self.testing_setup.setEnabled(self.rp_connected and self.motors)

        self.infoboxes_layout.addWidget(self.testing_setup, 1)

        # Create a widget to hold all 3 InfoBoxes
        self.infoboxes_container = QWidget()
        self.infoboxes_container.setObjectName("infoboxesContainer")
        self.infoboxes_container.setLayout(self.infoboxes_layout)

        # Create vertical splitter
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.layout.addWidget(self.splitter, 6)

        # Top section: InfoBoxes
        self.splitter.addWidget(self.infoboxes_container)

        # Bottom section: Log
        self.log_output = QTextEdit()
        self.log_output.setObjectName("logOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Log outputs will appear here...")

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

        self.worker.success.connect(self.rp_connection_success)
        self.worker.error.connect(self.rp_connection_error)
        self.worker.finished.connect(
            lambda: self.rp_connect_button.setEnabled(True)
        )

        self.rp_connect_button.setEnabled(False)
        self.worker.start()

    def rp_connection_success(self, ssh):
        if self.ssh is not None:
            self.ssh.close()
        self.ssh = ssh
        self.log("Successfully connected!", "success")
        self.rp_connected = True
        self.motor_pin_setup.setEnabled(True)
        self.testing_setup.setEnabled(self.rp_connected and self.motor_pins)

    def rp_connection_error(self, message):
        self.log(f"Connection failed: {message}", "error")
        self.motor_pin_setup.setEnabled(False)

    def save_motor_pins(self):
        self.log("Saving motor pin connections to motor_pin_config.json")

        try:
            en17 = int(self.en_17.text())
            dir17 = int(self.dir_17.text())
            step17 = int(self.step_17.text())
            self.log(f"Nema 17 Connections: enable pin: {en17}, dir pin: {dir17}, step pin: {step17}")
            m0 = int(self.M0_17.text())
            m1 = int(self.M1_17.text())
            m2 = int(self.M2_17.text())
            self.log(f"Nema 17 Microstep Connections: M0 pin: {m0}, M1 pin: {m1}, M2 pin: {m2}")
            en23 = int(self.en_23.text())
            step23 = int(self.step_23.text())
            dir23 = int(self.dir_23.text())
            self.log(f"Nema 23 Connections: enable pin: {en23}, dir pin: {dir23}, step pin: {step23}")

            config = {
                "nema17": {
                    "dir": dir17,
                    "step": step17,
                    "enable": en17,
                    "m0": m0,
                    "m1": m1,
                    "m2": m2
                },
                "nema23": {
                    "dir": dir23,
                    "step": step23,
                    "enable": en23
                }
            }

            with open("motor_pin_config.json", "w") as file:
                json.dump(config, file, indent=4)

        except ValueError as e:
            self.log(f"Invalid pin configuration: {e}", "error")
            return

        except OSError as e:
            self.log(f"Could not save file: {e}", "error")
            return

        self.log("Motor pin configuration saved!", "success")
        self.motor_pins = True
        self.test_motors_button.setEnabled(self.rp_connected and self.motor_pins)

    def open_motor_test_window(self):
        self.motor_window = MotorTestWindow(self.ssh)
        self.motor_window.show()

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
            f'<span style="color: {color};">{escape(str(message))}</span>'
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # More consistent widget rendering across OS themes

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())