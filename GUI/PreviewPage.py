import os
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QApplication, 
                             QSizePolicy, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent
from qfluentwidgets import SubtitleLabel, PushButton, InfoBar, InfoBarPosition
from .WebLive2DWidget import WebLive2DWidget

class PreviewPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('previewPage')  # Required for navigation
        
        # 启用拖拽功能
        self.setAcceptDrops(True)
        
        # 当前加载的模型路径
        self.current_model_path = None
        
        self.setupUI()
        
        # 响应窗口大小变化
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def setupUI(self):
        """设置简化的用户界面"""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        # Header with title and basic controls
        self.header_layout = QHBoxLayout()
        
        # Title
        self.title_label = SubtitleLabel("Live2D 模型预览器", self)
        self.header_layout.addWidget(self.title_label)
        
        # Spacer
        self.header_layout.addStretch()
        
        # Quick load button (for fallback)
        self.quick_load_button = PushButton("快速加载", self)
        self.quick_load_button.clicked.connect(self.quick_load_model)
        self.header_layout.addWidget(self.quick_load_button)
        
        self.main_layout.addLayout(self.header_layout)
        
        # Web-based Live2D Widget (takes up most of the space)
        self.live2d_widget = WebLive2DWidget(self)
        self.live2d_widget.setMinimumSize(800, 600)
        self.main_layout.addWidget(self.live2d_widget, 1)
        
        # Status bar
        self.status_label = QLabel("拖拽Live2D模型文件夹到此处，或点击左侧控制面板选择文件夹", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #606060; 
                font-style: italic; 
                padding: 8px;
                background-color: rgba(240, 240, 240, 0.5);
                border-radius: 4px;
                margin: 5px;
            }
        """)
        self.main_layout.addWidget(self.status_label)
        
        # Connect signals
        self.live2d_widget.modelLoaded.connect(self.on_model_loaded)
        self.live2d_widget.modelLoadFailed.connect(self.on_model_load_failed)
        self.live2d_widget.statusChanged.connect(self.on_status_changed)
        
    def quick_load_model(self):
        """快速加载模型（备用方法）"""
        default_path = "D:/1awd/game/output" if os.path.exists("D:/1awd/game/output") else ""
        folder_path = QFileDialog.getExistingDirectory(
            self, "选择Live2D模型文件夹", default_path
        )
        
        if folder_path:
            self.live2d_widget.loadModelFromFolder(folder_path)
            
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            # 检查是否为文件夹或.json文件
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                if os.path.isdir(path) or path.lower().endswith('.json'):
                    event.acceptProposedAction()
                    self.status_label.setText("松开鼠标以加载模型")
                    return
        event.ignore()
        
    def dragLeaveEvent(self, event):
        """拖拽离开事件"""
        self.status_label.setText("拖拽Live2D模型文件夹到此处，或点击左侧控制面板选择文件夹")
        
    def dropEvent(self, event: QDropEvent):
        """拖拽放下事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                
                if os.path.isdir(path):
                    # 如果是文件夹，直接加载
                    self.live2d_widget.loadModelFromFolder(path)
                elif path.lower().endswith('.json'):
                    # 如果是json文件，加载其所在文件夹
                    folder_path = os.path.dirname(path)
                    self.live2d_widget.loadModelFromFolder(folder_path)
                    
                event.acceptProposedAction()
                return
                
        event.ignore()
        self.status_label.setText("无效的文件类型，请拖拽Live2D模型文件夹或.json文件")
        
    def on_model_loaded(self, model_path):
        """模型加载成功回调"""
        self.current_model_path = model_path
        model_name = os.path.basename(os.path.dirname(model_path))
        self.status_label.setText(f"✅ 模型加载成功: {model_name}")
        
        # 显示成功信息条
        InfoBar.success(
            title="模型加载成功",
            content=f"已成功加载 {model_name}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        
    def on_model_load_failed(self, error_message):
        """模型加载失败回调"""
        self.status_label.setText(f"❌ 模型加载失败: {error_message}")
        
        # 显示错误信息条
        InfoBar.error(
            title="模型加载失败",
            content=error_message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
        
    def on_status_changed(self, status):
        """状态改变回调"""
        self.status_label.setText(status)
        
    def cleanup(self):
        """清理资源"""
        if hasattr(self.live2d_widget, 'cleanup'):
            self.live2d_widget.cleanup()
            
    def closeEvent(self, event):
        """窗口关闭事件"""
        self.cleanup()
        super().closeEvent(event)
