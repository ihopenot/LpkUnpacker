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
        file_group = QGroupBox("模型选择")
        file_layout = QVBoxLayout(file_group)

        self.select_folder_btn = QPushButton("选择模型文件夹")
        self.select_folder_btn.clicked.connect(self.selectModelFolder)
        file_layout.addWidget(self.select_folder_btn)

        self.model_path_label = QLabel("未选择模型")
        self.model_path_label.setWordWrap(True)
        self.model_path_label.setStyleSheet("color: gray; font-size: 10px;")
        file_layout.addWidget(self.model_path_label)

        layout.addWidget(file_group)

        # 表情控制区域
        expression_group = QGroupBox("表情控制")
        expression_layout = QVBoxLayout(expression_group)

        self.expression_combo = QComboBox()
        self.expression_combo.currentTextChanged.connect(self.onExpressionChanged)
        expression_layout.addWidget(self.expression_combo)

        layout.addWidget(expression_group)

        # 动作控制区域
        motion_group = QGroupBox("动作控制")
        motion_layout = QVBoxLayout(motion_group)

        self.motion_list = QListWidget()
        self.motion_list.itemClicked.connect(self.onMotionClicked)
        motion_layout.addWidget(self.motion_list)

        layout.addWidget(motion_group)

        # 参数控制区域
        param_group = QGroupBox("参数调节")
        param_layout = QVBoxLayout(param_group)

        eye_label = QLabel("眼部开合:")
        self.eye_slider = QSlider(Qt.Horizontal)
        self.eye_slider.setRange(0, 100)
        self.eye_slider.setValue(100)
        self.eye_slider.valueChanged.connect(self.onEyeChanged)
        param_layout.addWidget(eye_label)
        param_layout.addWidget(self.eye_slider)

        mouth_label = QLabel("嘴部开合:")
        self.mouth_slider = QSlider(Qt.Horizontal)
        self.mouth_slider.setRange(0, 100)
        self.mouth_slider.setValue(0)
        self.mouth_slider.valueChanged.connect(self.onMouthChanged)
        param_layout.addWidget(mouth_label)
        param_layout.addWidget(self.mouth_slider)

        angle_label = QLabel("头部角度:")
        self.angle_slider = QSlider(Qt.Horizontal)
        self.angle_slider.setRange(-30, 30)
        self.angle_slider.setValue(0)
        self.angle_slider.valueChanged.connect(self.onAngleChanged)
        param_layout.addWidget(angle_label)
        param_layout.addWidget(self.angle_slider)

        layout.addWidget(param_group)

        # 状态信息
        status_group = QGroupBox("状态信息")
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
            self, "选择Live2D模型文件夹",
            "D:/1awd/game/output" if os.path.exists("D:/1awd/game/output") else ""
        )

        if folder_path:
            self.loadModelFromFolder(folder_path)

    def loadModelFromFolder(self, folder_path):
        """从文件夹加载Live2D模型"""
        self.current_model_path = folder_path
        self.model_path_label.setText(f"模型路径: {folder_path}")

        # 查找模型文件
        model_files = list(Path(folder_path).glob("*.json"))
        if not model_files:
            self.statusChanged.emit("未找到模型文件")
            self.addStatusMessage("错误: 未找到.json模型文件")
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
            self.addStatusMessage(f"成功加载模型: {model_file.name}")

        except Exception as e:
            self.modelLoadFailed.emit(str(e))
            self.addStatusMessage(f"加载模型失败: {str(e)}")

    def updateControlsFromModel(self):
        """根据模型数据更新控制界面"""
        if not self.model_data:
            return

        # 表情
        self.expression_combo.clear()
        self.expression_combo.addItem("默认")
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
        if expression and expression != "默认":
            self.sendMessageToWeb('setExpression', {'expression': expression})
            self.addStatusMessage(f"切换表情: {expression}")

    def onMotionClicked(self, item):
        """动作点击事件"""
        motion_file = item.data(Qt.UserRole)
        if motion_file:
            self.sendMessageToWeb('playMotion', {'motion': motion_file})
            self.addStatusMessage(f"播放动作: {item.text()}")

    def onEyeChanged(self, value):
        """眼部参数改变"""
        eye_value = value / 100.0
        self.sendMessageToWeb('setParameter', {'parameter': 'eyeOpen', 'value': eye_value})

    def onMouthChanged(self, value):
        """嘴部参数改变"""
        mouth_value = value / 100.0
        self.sendMessageToWeb('setParameter', {'parameter': 'mouthOpen', 'value': mouth_value})

    def onAngleChanged(self, value):
        """角度参数改变"""
        self.sendMessageToWeb('setParameter', {'parameter': 'angleZ', 'value': value})

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

    def cleanup(self):
        """清理资源（当前为无操作，占位）"""
        pass