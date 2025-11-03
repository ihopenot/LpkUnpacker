import os
import sys
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QListWidget, QListWidgetItem, QGroupBox, QSlider, QComboBox, QTextEdit, QSplitter
)
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtGui import QFont


class WebLive2DWidget(QWidget):
    """基于Web技术的Live2D预览器，统一使用本地静态HTML"""

    modelLoaded = pyqtSignal(str)
    modelLoadFailed = pyqtSignal(str)
    statusChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_model_path = None
        self.model_data = {}
        self.setupUI()
        self.setupWebContent()

    def setupUI(self):
        """设置用户界面"""
        layout = QHBoxLayout(self)

        # 左侧控制面板
        control_panel = self.createControlPanel()

        # 右侧预览区域
        preview_panel = self.createPreviewPanel()

        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(control_panel)
        splitter.addWidget(preview_panel)
        splitter.setStretchFactor(0, 0)  # 控制面板固定宽度
        splitter.setStretchFactor(1, 1)  # 预览区域可伸缩
        splitter.setSizes([300, 700])

        layout.addWidget(splitter)

    def createControlPanel(self):
        """创建左侧控制面板"""
        panel = QWidget()
        panel.setMaximumWidth(300)
        panel.setMinimumWidth(250)
        layout = QVBoxLayout(panel)

        # 文件选择区域
        file_group = QGroupBox("Model Selection")
        file_layout = QVBoxLayout(file_group)

        self.select_folder_btn = QPushButton("Select Model Folder")
        self.select_folder_btn.clicked.connect(self.selectModelFolder)
        file_layout.addWidget(self.select_folder_btn)

        self.model_path_label = QLabel("No model selected")
        self.model_path_label.setWordWrap(True)
        self.model_path_label.setStyleSheet("color: gray; font-size: 10px;")
        file_layout.addWidget(self.model_path_label)

        layout.addWidget(file_group)

        # 表情控制区域
        expression_group = QGroupBox("Expression Control")
        expression_layout = QVBoxLayout(expression_group)

        self.expression_combo = QComboBox()
        self.expression_combo.currentTextChanged.connect(self.onExpressionChanged)
        expression_layout.addWidget(self.expression_combo)

        layout.addWidget(expression_group)

        # 动作控制区域
        motion_group = QGroupBox("Motion Control")
        motion_layout = QVBoxLayout(motion_group)

        self.motion_list = QListWidget()
        self.motion_list.itemClicked.connect(self.onMotionClicked)
        motion_layout.addWidget(self.motion_list)

        layout.addWidget(motion_group)

        # 独立窗口控制区域
        window_group = QGroupBox("Independent Window")
        window_layout = QVBoxLayout(window_group)

        self.open_window_btn = QPushButton("Open Independent Preview Window")
        self.open_window_btn.clicked.connect(self.openIndependentWindow)
        self.open_window_btn.setEnabled(False)  # 初始禁用，加载模型后启用
        window_layout.addWidget(self.open_window_btn)

        layout.addWidget(window_group)

        # 画布设置区域
        canvas_group = QGroupBox("Canvas Settings")
        canvas_layout = QVBoxLayout(canvas_group)

        # 画布透明度
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.onOpacityChanged)
        self.opacity_label = QLabel("100%")
        self.opacity_label.setMinimumWidth(40)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        canvas_layout.addLayout(opacity_layout)

        # 模型旋转
        rotation_layout = QHBoxLayout()
        rotation_layout.addWidget(QLabel("Rotation:"))
        self.rotation_slider = QSlider(Qt.Horizontal)
        self.rotation_slider.setRange(-180, 180)
        self.rotation_slider.setValue(0)
        self.rotation_slider.valueChanged.connect(self.onRotationChanged)
        self.rotation_label = QLabel("0°")
        self.rotation_label.setMinimumWidth(40)
        rotation_layout.addWidget(self.rotation_slider)
        rotation_layout.addWidget(self.rotation_label)
        canvas_layout.addLayout(rotation_layout)

        layout.addWidget(canvas_group)

        # 背景设置区域
        bg_group = QGroupBox("Background Settings")
        bg_layout = QVBoxLayout(bg_group)

        self.transparent_bg_btn = QPushButton("Transparent Background")
        self.transparent_bg_btn.setCheckable(True)
        self.transparent_bg_btn.setChecked(True)
        self.transparent_bg_btn.clicked.connect(self.onBackgroundChanged)
        bg_layout.addWidget(self.transparent_bg_btn)

        self.colored_bg_btn = QPushButton("Colored Background")
        self.colored_bg_btn.setCheckable(True)
        self.colored_bg_btn.clicked.connect(self.onBackgroundChanged)
        bg_layout.addWidget(self.colored_bg_btn)

        layout.addWidget(bg_group)

        # 状态信息
        status_group = QGroupBox("Status Information")
        status_layout = QVBoxLayout(status_group)

        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        self.status_text.setFont(QFont("Consolas", 8))
        status_layout.addWidget(self.status_text)

        layout.addWidget(status_group)

        layout.addStretch()
        return panel

    def createPreviewPanel(self):
        """创建右侧预览面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Web视图
        self.web_view = QWebEngineView()
        # 允许本地HTML访问远程CDN与本地文件URL
        try:
            settings = self.web_view.settings()
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        except Exception as e:
            print(f"Warn: failed to apply QWebEngineSettings - {e}")
        self.web_view.setMinimumSize(400, 400)
        layout.addWidget(self.web_view)

        return panel

    def setupWebContent(self):
        """设置Web内容（加载静态HTML）"""
        # 兼容打包后的资源路径
        if getattr(sys, 'frozen', False):
            # 打包后的可执行文件 - Nuitka会将资源放在可执行文件同目录
            base_path = Path(sys.executable).parent
            # 尝试多个可能的路径
            possible_paths = [
                base_path / "GUI" / "assets" / "live2d" / "index.html",
                base_path / "assets" / "live2d" / "index.html", 
                Path(os.getcwd()) / "GUI" / "assets" / "live2d" / "index.html"
            ]
        else:
            # 开发环境
            base_path = Path(__file__).parent
            possible_paths = [
                base_path / "assets" / "live2d" / "index.html",
                base_path.parent / "GUI" / "assets" / "live2d" / "index.html"
            ]
            
        assets_path = None
        for path in possible_paths:
            if path.exists():
                assets_path = path
                break
                
        if assets_path is None:
            err = f"缺少Web预览HTML文件，尝试过的路径: {[str(p) for p in possible_paths]}"
            print(err)
            self.statusChanged.emit(err)
            return
            
        print(f"加载Live2D HTML文件: {assets_path}")
        self.web_view.load(QUrl.fromLocalFile(str(assets_path.resolve())))

    def selectModelFolder(self):
        """选择模型文件夹"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Live2D Model Folder",
            "D:/1awd/game/output" if os.path.exists("D:/1awd/game/output") else ""
        )

        if folder_path:
            self.loadModelFromFolder(folder_path)

    def loadModelFromFolder(self, folder_path):
        """从文件夹加载Live2D模型"""
        self.current_model_path = folder_path
        self.model_path_label.setText(f"Model Path: {folder_path}")

        # 查找模型文件
        model_files = list(Path(folder_path).glob("*.json"))
        if not model_files:
            self.statusChanged.emit("Model file not found")
            self.addStatusMessage("Error: No .json model file found")
            return

        model_file = model_files[0]

        try:
            with open(model_file, 'r', encoding='utf-8') as f:
                self.model_data = json.load(f)
            if isinstance(self.model_data, dict):
                self.model_data['path'] = str(model_file)

            self.updateControlsFromModel()

            model_url = QUrl.fromLocalFile(str(model_file)).toString()
            self.sendMessageToWeb('loadModel', {
                'modelPath': str(model_file),
                'modelUrl': model_url,
                'modelData': self.model_data
            })

            self.modelLoaded.emit(str(model_file))
            self.addStatusMessage(f"Successfully loaded model: {model_file.name}")
            
            # 启用独立窗口按钮
            self.open_window_btn.setEnabled(True)

        except Exception as e:
            self.modelLoadFailed.emit(str(e))
            self.addStatusMessage(f"Failed to load model: {str(e)}")

    def updateControlsFromModel(self):
        """根据模型数据更新控制界面"""
        if not self.model_data:
            return

        # 表情
        self.expression_combo.clear()
        self.expression_combo.addItem("Default")
        if 'FileReferences' in self.model_data and 'Expressions' in self.model_data['FileReferences']:
            expressions = self.model_data['FileReferences']['Expressions']
            if isinstance(expressions, list):
                for expr in expressions:
                    if isinstance(expr, dict) and 'Name' in expr:
                        self.expression_combo.addItem(expr['Name'])

        # 动作
        self.motion_list.clear()
        if 'FileReferences' in self.model_data and 'Motions' in self.model_data['FileReferences']:
            motions = self.model_data['FileReferences']['Motions']
            if isinstance(motions, dict):
                for category, motion_list in motions.items():
                    if isinstance(motion_list, list):
                        for motion in motion_list:
                            if isinstance(motion, dict) and 'File' in motion:
                                item = QListWidgetItem(f"{category}: {Path(motion['File']).stem}")
                                item.setData(Qt.UserRole, motion['File'])
                                self.motion_list.addItem(item)

    def onExpressionChanged(self, expression):
        """表情改变事件"""
        if expression and expression != "Default":
            self.sendMessageToWeb('setExpression', {'expression': expression})
            self.addStatusMessage(f"Switch expression: {expression}")

    def onMotionClicked(self, item):
        """动作点击事件"""
        motion_file = item.data(Qt.UserRole)
        if motion_file:
            self.sendMessageToWeb('playMotion', {'motion': motion_file})
            self.addStatusMessage(f"Play motion: {item.text()}")

    def openIndependentWindow(self):
        """打开独立Live2D预览窗口"""
        if not self.current_model_path:
            self.addStatusMessage("Error: No model selected")
            return
            
        # 查找模型文件
        model_files = list(Path(self.current_model_path).glob("*.json"))
        if not model_files:
            self.addStatusMessage("Error: Model file not found")
            return
            
        model_file = model_files[0]
        
        try:
            # 导入Live2DPreviewWindow
            from GUI.Live2DPreviewWindow import Live2DPreviewWindow
            
            # 创建并显示独立预览窗口
            self.preview_window = Live2DPreviewWindow(str(model_file))
            self.preview_window.show()
            self.addStatusMessage(f"Opened independent preview window: {model_file.name}")
            
        except ImportError:
            self.addStatusMessage("Error: Live2D independent preview feature unavailable")
        except Exception as e:
            self.addStatusMessage(f"Failed to open independent window: {str(e)}")

    def sendMessageToWeb(self, msg_type, data):
        """向Web视图发送消息"""
        script = f"""
        if (window.live2dPreview) {{
            window.live2dPreview.handleMessage({{
                type: '{msg_type}',
                ...{json.dumps(data)}
            }});
        }}
        """
        self.web_view.page().runJavaScript(script)

    def addStatusMessage(self, message):
        """添加状态消息"""
        self.status_text.append(message)
        cursor = self.status_text.textCursor()
        cursor.movePosition(cursor.End)
        self.status_text.setTextCursor(cursor)

    def onOpacityChanged(self, value):
        """画布透明度改变事件"""
        opacity = value / 100.0
        self.opacity_label.setText(f"{value}%")
        self.sendMessageToWeb('setCanvasOpacity', {'opacity': opacity})
        self.addStatusMessage(f"Set canvas opacity: {value}%")

    def onRotationChanged(self, value):
        """模型旋转改变事件"""
        self.rotation_label.setText(f"{value}°")
        self.sendMessageToWeb('setRotationAngle', {'angle': value})
        self.addStatusMessage(f"Set model rotation: {value}°")

    def onBackgroundChanged(self):
        """背景设置改变事件"""
        sender = self.sender()
        if sender == self.transparent_bg_btn:
            if self.transparent_bg_btn.isChecked():
                self.colored_bg_btn.setChecked(False)
                self.sendMessageToWeb('setBackground', {'transparent': True})
                self.addStatusMessage("Set transparent background")
        elif sender == self.colored_bg_btn:
            if self.colored_bg_btn.isChecked():
                self.transparent_bg_btn.setChecked(False)
                # 默认使用白色背景
                self.sendMessageToWeb('setBackground', {'transparent': False, 'color': '#ffffff'})
                self.addStatusMessage("Set colored background")

    def cleanup(self):
        """清理资源（当前为无操作，占位）"""
        pass