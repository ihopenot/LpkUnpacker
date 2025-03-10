from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    SubtitleLabel, PushButton, InfoBar, InfoBarPosition, LineEdit,
    FluentIcon, ComboBox, ProgressBar
)

class EncryptionPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('encryptionPage')  # Required for navigation
        
        self.setupUI()
        
    def setupUI(self):
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        # Title
        self.title_label = SubtitleLabel("Encryption Package Extractor", self)
        self.main_layout.addWidget(self.title_label)
        
        # Description
        self.desc_label = QLabel(
            "This tool can extract files from unity game/live2d mod by using UnityPy library.",
            self
        )
        self.desc_label.setWordWrap(True)
        self.main_layout.addWidget(self.desc_label)
        
        # Package file selection
        self.package_layout = QHBoxLayout()
        self.package_label = SubtitleLabel("Package File:", self)
        self.package_edit = LineEdit(self)
        self.package_edit.setPlaceholderText("Select encrypted package file...")
        self.package_button = PushButton("Browse", self)
        self.package_button.setIcon(FluentIcon.FOLDER)
        self.package_button.clicked.connect(self.browse_package)
        self.package_layout.addWidget(self.package_label)
        self.package_layout.addWidget(self.package_edit, 1)
        self.package_layout.addWidget(self.package_button)
        self.main_layout.addLayout(self.package_layout)
        
        # Encryption type selection
        self.type_layout = QHBoxLayout()
        self.type_label = SubtitleLabel("Encryption Type:", self)
        self.type_combo = ComboBox(self)
        self.type_combo.addItems(["All", "Img", "Obj"])
        self.type_combo.setCurrentIndex(0)
        self.type_layout.addWidget(self.type_label)
        self.type_layout.addWidget(self.type_combo)
        self.type_layout.addStretch(1)
        self.main_layout.addLayout(self.type_layout)
        
        # Output directory selection
        self.output_layout = QHBoxLayout()
        self.output_label = SubtitleLabel("Output Directory:", self)
        self.output_edit = LineEdit(self)
        self.output_edit.setPlaceholderText("Select output directory...")
        self.output_button = PushButton("Browse", self)
        self.output_button.setIcon(FluentIcon.FOLDER)
        self.output_button.clicked.connect(self.browse_output)
        self.output_layout.addWidget(self.output_label)
        self.output_layout.addWidget(self.output_edit, 1)
        self.output_layout.addWidget(self.output_button)
        self.main_layout.addLayout(self.output_layout)
        
        # Progress bar
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.main_layout.addWidget(self.progress_bar)
        
        # Extract button
        self.extract_button = PushButton("Extract Package", self)
        self.extract_button.setIcon(FluentIcon.PLAY)
        self.extract_button.clicked.connect(self.start_extraction)
        self.main_layout.addWidget(self.extract_button)
        
        # Feature notice
        self.notice_frame = QFrame(self)
        self.notice_frame.setStyleSheet("background-color: #f0f0f0; border-radius: 5px;")
        notice_layout = QVBoxLayout(self.notice_frame)
        
        notice_title = SubtitleLabel("Coming Soon", self.notice_frame)
        notice_desc = QLabel(
            "The encryption package extraction feature is currently under development and will be available in a future update.",
            self.notice_frame
        )
        notice_desc.setWordWrap(True)
        
        notice_layout.addWidget(notice_title)
        notice_layout.addWidget(notice_desc)
        
        self.main_layout.addWidget(self.notice_frame)
        self.main_layout.addStretch(1)
        
    def browse_package(self):
        InfoBar.info(
            title="Feature Not Available",
            content="Encryption package extraction is not implemented yet.",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000
        )
        
    def browse_output(self):
        InfoBar.info(
            title="Feature Not Available", 
            content="Encryption package extraction is not implemented yet.",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000
        )
        
    def start_extraction(self):
        InfoBar.info(
            title="Coming Soon",
            content="Game file extraction will be available in a future update.",
            parent=self, 
            position=InfoBarPosition.TOP,
            duration=3000
        )
