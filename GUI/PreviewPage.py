import os
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QApplication, 
                             QSizePolicy, QPushButton, QFileDialog, QSplitter, QGroupBox)
from PyQt5.QtCore import Qt, QCoreApplication, pyqtSignal
from PyQt5.QtGui import QFont
from qfluentwidgets import SubtitleLabel, PushButton, InfoBar, InfoBarPosition

# Try to import Live2D components
try:
    from GUI.WebLive2DWidget import WebLive2DWidget
    LIVE2D_AVAILABLE = True
except ImportError as e:
    print(f"Live2D components not available: {e}")
    LIVE2D_AVAILABLE = False

try:
    from GUI.Live2DPreviewWindow import Live2DPreviewWindow
    NATIVE_LIVE2D_AVAILABLE = True
except ImportError as e:
    print(f"Native Live2D components not available: {e}")
    NATIVE_LIVE2D_AVAILABLE = False


class PreviewPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('previewPage')  # Required for navigation
        self.current_model_path = None
        self.preview_window = None
        
        self.setupUI()
        # 应用退出前做一次兜底清理，防止文件句柄未及时释放
        try:
            app = QCoreApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(self._cleanup_temp_model_json)
        except Exception:
            pass

    def setupUI(self):
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        # Title
        self.title_label = SubtitleLabel("Live2D Preview", self)
        self.main_layout.addWidget(self.title_label)

        if LIVE2D_AVAILABLE:
            self.setupLive2DUI()
        else:
            self.setupFallbackUI()
            
    def setupLive2DUI(self):
        """设置Live2D预览界面"""
        # 控制按钮区域
        control_frame = QFrame(self)
        control_layout = QHBoxLayout(control_frame)
        
        # 选择模型按钮
        self.select_model_btn = PushButton("选择Live2D模型", self)
        self.select_model_btn.clicked.connect(self.selectModel)
        control_layout.addWidget(self.select_model_btn)
        
        # 打开独立预览窗口按钮
        if NATIVE_LIVE2D_AVAILABLE:
            self.open_window_btn = PushButton("打开独立预览窗口", self)
            self.open_window_btn.clicked.connect(self.openPreviewWindow)
            self.open_window_btn.setEnabled(False)
            control_layout.addWidget(self.open_window_btn)
        
        control_layout.addStretch()
        self.main_layout.addWidget(control_frame)
        
        # Live2D预览区域
        try:
            self.live2d_widget = WebLive2DWidget(self)
            self.main_layout.addWidget(self.live2d_widget, 1)
            
            # 连接信号
            self.live2d_widget.modelLoaded.connect(self.onModelLoaded)
            self.live2d_widget.modelLoadFailed.connect(self.onModelLoadFailed)
            
        except Exception as e:
            print(f"Error creating WebLive2DWidget: {e}")
            self.setupFallbackUI()
    
    def setupFallbackUI(self):
        """设置回退界面（当Live2D组件不可用时）"""
        # Error frame
        self.error_frame = QFrame(self)
        self.error_frame.setStyleSheet("""
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 20px;
        """)
        error_layout = QVBoxLayout(self.error_frame)
        
        # Header
        error_title = SubtitleLabel("Live2D功能不可用", self.error_frame)
        error_title.setAlignment(Qt.AlignCenter)
        error_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #856404;")
        
        # Description
        description = QLabel(
            "Live2D预览功能需要额外的依赖包。请确保已安装以下依赖：\n\n"
            "• live2d-py >= 0.5.4\n"
            "• PyQtWebEngine >= 5.15.0\n\n"
            "您可以运行以下命令安装：\n"
            "pip install live2d-py PyQtWebEngine",
            self.error_frame
        )
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 14px; color: #856404; margin: 10px;")
        
        # Install button
        install_btn = PushButton("尝试自动安装依赖", self.error_frame)
        install_btn.clicked.connect(self.tryInstallDependencies)
        
        # Add widgets to layout
        error_layout.addWidget(error_title)
        error_layout.addWidget(description)
        error_layout.addWidget(install_btn, 0, Qt.AlignCenter)
        error_layout.setAlignment(Qt.AlignCenter)
        
        # Add to main layout
        self.main_layout.addWidget(self.error_frame, 1)
    
    def selectModel(self):
        """选择Live2D模型"""
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "选择Live2D模型文件夹",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder_path:
            self.current_model_path = folder_path
            if hasattr(self, 'live2d_widget'):
                self.live2d_widget.loadModelFromFolder(folder_path)
    
    def openPreviewWindow(self):
        """打开独立的Live2D预览窗口"""
        if not self.current_model_path:
            InfoBar.warning(
                title="提示",
                content="请先选择一个Live2D模型",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        try:
            # 查找模型文件
            model_file = None
            for file in os.listdir(self.current_model_path):
                if file.endswith('.model3.json'):
                    model_file = os.path.join(self.current_model_path, file)
                    break
            
            if not model_file:
                InfoBar.error(
                    title="错误",
                    content="在选定文件夹中未找到.model3.json文件",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return
            
            # 关闭之前的预览窗口
            if self.preview_window:
                self.preview_window.close()
            
            # 创建新的预览窗口
            self.preview_window = Live2DPreviewWindow(model_file)
            self.preview_window.show()
            
        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"打开预览窗口失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def onModelLoaded(self, model_path):
        """模型加载成功回调"""
        if NATIVE_LIVE2D_AVAILABLE and hasattr(self, 'open_window_btn'):
            self.open_window_btn.setEnabled(True)
        
        InfoBar.success(
            title="成功",
            content="Live2D模型加载成功",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def onModelLoadFailed(self, error_msg):
        """模型加载失败回调"""
        InfoBar.error(
            title="加载失败",
            content=f"Live2D模型加载失败: {error_msg}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
    
    def tryInstallDependencies(self):
        """尝试自动安装依赖"""
        InfoBar.info(
            title="提示",
            content="请在终端中手动运行: pip install live2d-py PyQtWebEngine",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
    
    def _cleanup_temp_model_json(self):
        """清理临时文件"""
        try:
            if hasattr(self, 'live2d_widget') and self.live2d_widget:
                self.live2d_widget.cleanup()
        except Exception:
            pass
        
        try:
            if self.preview_window:
                self.preview_window.close()
        except Exception:
            pass
            
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
