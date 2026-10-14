import sys
import time
import math
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QMainWindow,
    QProgressBar, QLabel, QLineEdit, QFormLayout, QGroupBox, QPlainTextEdit,
    QHBoxLayout, QMessageBox, QDialog, QInputDialog)


from controller import Controller, ControlWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Sundial Control Panel")
        self.setGeometry(100, 100, 1000, 700)

        self.dut_names = [f"DUT {i}" for i in range(12)]
        self.dut_buttons = []
        self.dut_busy = False
        self.dut_worker = None
        self.selected_dut_index = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.controller = Controller()
        self.init_ui()
        self.Worker = None

    def init_ui(self):
        self.control_panel = QVBoxLayout(self)
        self.status_label = QPlainTextEdit("hello")
        self.status_label.setReadOnly(True)
        self.connect_device_button = QPushButton("Connect To Device")
        self.disconnect_device_button = QPushButton("Disconnect Device")
        self.connect_device_button.clicked.connect(self.connect_to_pi)
        self.control_panel.addWidget(self.status_label)
        self.control_panel.addWidget(self.connect_device_button)
        self.control_panel.addWidget(self.disconnect_device_button)

        # SET OF 3 BUTTONS, 1 FOR EACH STEP
        self.connectRP = QPushButton("Connect to Raspberry Pi")
        self.testMotors = QPushButton("Test Motors")
        self.startTest = QPushButton("Start Test")
        self.stepsLayout = QHBoxLayout()
        self.stepsLayout.addWidget(self.connectRP)
        self.stepsLayout.addWidget(self.testMotors)
        self.stepsLayout.addWidget(self.startTest)

        self.control_panel.addLayout(self.stepsLayout)

        # SCROLLABLE LOG BOX
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Log messages will appear here...")
        self.log_box.setMaximumBlockCount(1000)  # Limit the number of lines in the log box

        self.toggle_log = QPushButton("Hide Log")
        self.toggle_log.clicked.connect(self.toggle_log_visibility)

        self.stepsLayout.addWidget(self.log_box)
        self.control_panel.addWidget(self.toggle_log)

        #DUT Board Configuration button
        self.config_button = QPushButton("Configure DUT Board")
        self.config_button.clicked.connect(self.configure_dut)
        self.control_panel.addWidget(self.config_button)

        self.central_widget.setLayout(self.control_panel) #sets control panel to central widget

    def toggle_log_visibility(self):
        if self.log_box.isVisible():
            self.log_box.hide()
            self.toggle_log.setText("Show Log")
        else:
            self.log_box.show()
            self.toggle_log.setText("Hide Log")

    def connect_to_pi(self):
        self.worker = ControlWorker(self.controller)
        print("made a worker thread")
        self.worker.progress.connect(self.status_label.appendPlainText)
        self.worker.progress.connect(lambda msg: print("RECEIVED PROGRESS SIGNAL:", msg))
        print("connected progress signal")
        self.worker.start()

    def configure_dut(self):
        self.dut_buttons = []
        popup = QDialog(self)
        popup.setWindowTitle("Configure DUT Board")

        image = QPixmap("clock.png")

        if image.isNull():
            QMessageBox.warning(self, "Image error", "Could not load clock.png")
            return

        image = image.scaled(
            600, 600,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        width = image.width()
        height = image.height()

        popup.setFixedSize(width, height)

        image_label = QLabel(popup)
        image_label.setPixmap(image)
        image_label.setGeometry(0, 0, width, height)

        button_width = 100
        button_height = 40

        rename_width = 60
        rename_height = 25

        center_x = width / 2
        center_y = height / 2

        radius = max(
            0,
            min(
                (width - button_width) // 2,
                (height - button_height) // 2
            ) - 10
        )

        rename_radius = max(0, radius - 70)

        for index, name in enumerate(self.dut_names):
            angle = math.radians(index * 30 - 90)

            # DUT selection button
            x = center_x + radius * math.cos(angle) - button_width / 2
            y = center_y + radius * math.sin(angle) - button_height / 2

            button = QPushButton(name, image_label)
            button.setGeometry(
                round(x), round(y), button_width, button_height
            )

            button.clicked.connect(
                lambda checked=False, i=index: self.select_dut(i)
            )

            self.dut_buttons.append(button)

            # Rename button, closer to the center
            rename_x = (
                    center_x
                    + rename_radius * math.cos(angle)
                    - rename_width / 2
            )
            rename_y = (
                    center_y
                    + rename_radius * math.sin(angle)
                    - rename_height / 2
            )

            rename_button = QPushButton("Rename", image_label)
            rename_button.setGeometry(
                round(rename_x), round(rename_y),
                rename_width, rename_height
            )

            rename_button.clicked.connect(
                lambda checked=False, i=index, b=button:
                self.rename_dut(i, b)
            )

        popup.exec()

    def select_dut(self, index):
        if self.dut_busy:
            return

        self.dut_busy = True

        for button in self.dut_buttons:
            button.setEnabled(not self.dut_busy)

        self.selected_dut_index = index
        name = self.dut_names[index]

        message = f"Selected index {index}: {name}"
        print(message)
        self.log_box.appendPlainText(message)

        # Start your DUT backend worker here.

    def rename_dut(self, index, button):
        name, accepted = QInputDialog.getText(
            button,
            "Rename DUT",
            f"Enter a name for DUT {index}:",
            text=self.dut_names[index]
        )

        if accepted and name.strip():
            self.dut_names[index] = name.strip()
            button.setText(self.dut_names[index])




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())