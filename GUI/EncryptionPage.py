from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    SubtitleLabel, PushButton, InfoBar, InfoBarPosition, LineEdit,
    FluentIcon, ComboBox, ProgressBar
)
from Translations import get_i18n, tr

class EncryptionPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('encryptionPage')  # Required for navigation
        self.i18n = get_i18n()
        
        self.setupUI()
        self.retranslate_ui()
        self.i18n.languageChanged.connect(self.retranslate_ui)
        
    def setupUI(self):
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        # Title
        self.title_label = SubtitleLabel("", self)
        self.main_layout.addWidget(self.title_label)
        
        # Description
        self.desc_label = QLabel("", self)
        self.desc_label.setWordWrap(True)
        self.main_layout.addWidget(self.desc_label)
        
        # Package file selection
        self.package_layout = QHBoxLayout()
        self.package_label = SubtitleLabel("", self)
        self.package_edit = LineEdit(self)
        self.package_button = PushButton("", self)
        self.package_button.setIcon(FluentIcon.FOLDER)
        self.package_button.clicked.connect(self.browse_package)
        self.package_layout.addWidget(self.package_label)
        self.package_layout.addWidget(self.package_edit, 1)
        self.package_layout.addWidget(self.package_button)
        self.main_layout.addLayout(self.package_layout)
        
        # Encryption type selection
        self.type_layout = QHBoxLayout()
        self.type_label = SubtitleLabel("", self)
        self.type_combo = ComboBox(self)
        self.type_combo.addItems(["All", "Img", "Obj"])
        self.type_combo.setCurrentIndex(0)
        self.type_layout.addWidget(self.type_label)
        self.type_layout.addWidget(self.type_combo)
        self.type_layout.addStretch(1)
        self.main_layout.addLayout(self.type_layout)
        
        # Output directory selection
        self.output_layout = QHBoxLayout()
        self.output_label = SubtitleLabel("", self)
        self.output_edit = LineEdit(self)
        self.output_button = PushButton("", self)
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
        self.extract_button = PushButton("", self)
        self.extract_button.setIcon(FluentIcon.PLAY)
        self.extract_button.clicked.connect(self.start_extraction)
        self.main_layout.addWidget(self.extract_button)
        
        # Feature notice
        self.notice_frame = QFrame(self)
        self.notice_frame.setStyleSheet("background-color: #f0f0f0; border-radius: 5px;")
        notice_layout = QVBoxLayout(self.notice_frame)
        
        self.notice_title = SubtitleLabel("", self.notice_frame)
        self.notice_desc = QLabel("", self.notice_frame)
        self.notice_desc.setWordWrap(True)
        
        notice_layout.addWidget(self.notice_title)
        notice_layout.addWidget(self.notice_desc)
        
        self.main_layout.addWidget(self.notice_frame)
        self.main_layout.addStretch(1)

    def retranslate_ui(self):
        self.title_label.setText(tr("encryption.title"))
        self.desc_label.setText(tr("encryption.description"))

        self.package_label.setText(tr("encryption.package_file"))
        self.package_edit.setPlaceholderText(tr("encryption.placeholder_package"))
        self.package_button.setText(tr("common.browse"))

        self.type_label.setText(tr("encryption.encryption_type"))

        self.output_label.setText(tr("encryption.output_directory"))
        self.output_edit.setPlaceholderText(tr("encryption.placeholder_output"))
        self.output_button.setText(tr("common.browse"))

        self.extract_button.setText(tr("encryption.extract_package"))
        self.notice_title.setText(tr("encryption.coming_soon"))
        self.notice_desc.setText(tr("encryption.notice_description"))
        
    def browse_package(self):
        InfoBar.info(
            title=tr("encryption.not_available_title"),
            content=tr("encryption.not_available_content"),
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000
        )
        
    def browse_output(self):
        InfoBar.info(
            title=tr("encryption.not_available_title"),
            content=tr("encryption.not_available_content"),
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000
        )
        
    def start_extraction(self):
        InfoBar.info(
            title=tr("encryption.coming_soon"),
            content=tr("encryption.future_update_content"),
            parent=self, 
            position=InfoBarPosition.TOP,
            duration=3000
        )
