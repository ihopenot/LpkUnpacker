import os
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QApplication, 
                             QSizePolicy, QPushButton, QFileDialog, QSplitter, QGroupBox, QButtonGroup)
from PyQt5.QtCore import Qt, QCoreApplication, pyqtSignal
from PyQt5.QtGui import QFont
from qfluentwidgets import SubtitleLabel, PushButton, InfoBar, InfoBarPosition, RadioButton

# Try to import Live2D components
try:
    from GUI.WebLive2DWidget import WebLive2DWidget
    LIVE2D_AVAILABLE = True
except ImportError as e:
    print(f"Live2D components not available: {e}")
    LIVE2D_AVAILABLE = False


class WebPreviewPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('webPreviewPage')  # Required for navigation
        self.current_model_path = None
        self.live2d_widget = None
        
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
        """设置Web Live2D预览界面"""
        # 控制按钮区域
        control_frame = QFrame(self)
        control_layout = QHBoxLayout(control_frame)
        
        # 选择模型按钮
        self.select_model_btn = PushButton("Select Live2D Model", self)
        self.select_model_btn.clicked.connect(self.selectModel)
        control_layout.addWidget(self.select_model_btn)
        
        control_layout.addStretch()
        self.main_layout.addWidget(control_frame)
        
        # Live2D预览区域容器
        self.preview_container = QFrame(self)
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.preview_container, 1)
        
        # 初始化web方法预览
        self.setupWebPreview()
    
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
        error_title = SubtitleLabel("Live2D Feature Unavailable", self.error_frame)
        error_title.setAlignment(Qt.AlignCenter)
        error_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #856404;")
        
        # Description
        description = QLabel(
            "Live2D preview feature requires additional dependencies. Please ensure the following packages are installed:\n\n"
            "• live2d-py >= 0.5.4\n"
            "• PyQtWebEngine >= 5.15.0\n\n"
            "You can install them by running:\n"
            "pip install live2d-py PyQtWebEngine",
            self.error_frame
        )
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 14px; color: #856404; margin: 10px;")
        
        # Install button
        install_btn = PushButton("Try Auto Install Dependencies", self.error_frame)
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
            "Select Live2D Model Folder",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder_path:
            self.current_model_path = folder_path
            
            # 加载模型
            if self.current_model_path:
                self.loadCurrentModel()
    
    def onModelLoaded(self, model_path):
        """模型加载成功回调"""        
        InfoBar.success(
            title="Success",
            content="Live2D model loaded successfully",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def onModelLoadFailed(self, error_msg):
        """模型加载失败回调"""
        InfoBar.error(
            title="Load Failed",
            content=f"Live2D model loading failed: {error_msg}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
    
    def setupWebPreview(self):
        """设置Web方法预览"""
        # 清除现有预览
        self.clearPreview()
        
        try:
            from GUI.WebLive2DWidget import WebLive2DWidget
            self.live2d_widget = WebLive2DWidget(self.preview_container)
            self.preview_layout.addWidget(self.live2d_widget)
            
            # 连接信号
            self.live2d_widget.modelLoaded.connect(self.onModelLoaded)
            self.live2d_widget.modelLoadFailed.connect(self.onModelLoadFailed)
            
        except Exception as e:
            print(f"Error creating WebLive2DWidget: {e}")
            self.showErrorMessage(f"Web method initialization failed: {str(e)}")
    
    def clearPreview(self):
        """清除当前预览组件"""
        if self.live2d_widget:
            try:
                # 断开信号连接
                if hasattr(self.live2d_widget, 'modelLoaded'):
                    self.live2d_widget.modelLoaded.disconnect()
                if hasattr(self.live2d_widget, 'modelLoadFailed'):
                    self.live2d_widget.modelLoadFailed.disconnect()
                
                # 清理组件
                if hasattr(self.live2d_widget, 'cleanup'):
                    self.live2d_widget.cleanup()
                
                self.live2d_widget.setParent(None)
                self.live2d_widget.deleteLater()
            except Exception as e:
                print(f"Error clearing preview: {e}")
            finally:
                self.live2d_widget = None
    
    def loadCurrentModel(self):
        """重新加载当前模型"""
        if self.current_model_path:
            # Web方法加载
            if self.live2d_widget and hasattr(self.live2d_widget, 'loadModelFromFolder'):
                self.live2d_widget.loadModelFromFolder(self.current_model_path)
            elif self.live2d_widget and hasattr(self.live2d_widget, 'loadModel'):
                self.live2d_widget.loadModel(self.current_model_path)
    
    def showErrorMessage(self, message):
        """显示错误消息"""
        InfoBar.error(
            title="Error",
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
    
    def tryInstallDependencies(self):
        """尝试自动安装依赖"""
        InfoBar.info(
            title="Info",
            content="Please run manually in terminal: pip install live2d-py PyQtWebEngine",
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
