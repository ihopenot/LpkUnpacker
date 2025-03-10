import os
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QLabel, QApplication, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from qfluentwidgets import SubtitleLabel

class PreviewPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('previewPage')  # Required for navigation
        
        self.setupUI()
        
        # 响应窗口大小变化
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def setupUI(self):
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        # Title
        self.title_label = SubtitleLabel("Live2D Preview", self)
        self.main_layout.addWidget(self.title_label)

        # Coming Soon frame
        self.coming_soon_frame = QFrame(self)
        self.coming_soon_frame.setStyleSheet("""
            background-color: #f0f0f0;
            border-radius: 8px;
            padding: 20px;
        """)
        coming_soon_layout = QVBoxLayout(self.coming_soon_frame)
        
        # Header
        coming_soon_title = SubtitleLabel("Coming Soon", self.coming_soon_frame)
        coming_soon_title.setAlignment(Qt.AlignCenter)
        coming_soon_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #606060;")
        
        # Description
        description = QLabel(
            "The Live2D model preview feature is under development and will be available in a future update.",
            self.coming_soon_frame
        )
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 14px; color: #505050; margin: 10px;")
        
        # Add widgets to layout
        coming_soon_layout.addWidget(coming_soon_title)
        coming_soon_layout.addWidget(description)
        coming_soon_layout.setAlignment(Qt.AlignCenter)
        
        # Add to main layout
        self.main_layout.addWidget(self.coming_soon_frame, 1)
            
    def updateUIScale(self, window_width, window_height):
        """根据窗口大小调整UI元素"""
        # 计算比例因子
        scale_factor = max(1.0, window_width / 1000.0)
        
        # 调整字体大小
        font = QApplication.instance().font()
        for label in self.findChildren(SubtitleLabel):
            label_font = label.font()
            label_font.setPointSize(font.pointSize() + 2)  # 标题字体比正常字体大2点
            label.setFont(label_font)
