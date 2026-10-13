import sys
import time
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QMainWindow,
    QProgressBar, QLabel, QLineEdit, QFormLayout, QGroupBox, QPlainTextEdit,
    QHBoxLayout, QMessageBox)

from controller import Controller, ControlWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Sundial Control Panel")
        self.setGeometry(100, 100, 1000, 700)

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
        self.central_widget.setLayout(self.control_panel)

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
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())