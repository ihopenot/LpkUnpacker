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


def _is_live2d_model_json(file_path: str) -> bool:
    """验证是否为有效的Live2D模型JSON文件"""
    try:
        # 检查文件名是否包含model
        file_name = os.path.basename(file_path).lower()
        if 'model' not in file_name or not file_name.endswith('.json'):
            return False
            
        # 检查JSON内容
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not isinstance(data, dict):
            return False
            
        # 检查Live2D v3模型的必要字段
        file_refs = data.get('FileReferences', {})
        if not isinstance(file_refs, dict):
            return False
            
        # 检查是否有Moc文件引用
        moc = file_refs.get('Moc')
        if isinstance(moc, str) and moc.lower().endswith('.moc3'):
            return True
            
        # 检查版本号
        version = data.get('Version')
        if isinstance(version, int) and version >= 3:
            return True
            
        return False
        
    except Exception:
        return False


def _find_valid_model_json(folder_path: str) -> str:
    """在文件夹中查找有效的Live2D模型JSON文件"""
    folder = Path(folder_path)
    
    # 优先查找包含model的JSON文件
    model_files = []
    for json_file in folder.glob("*.json"):
        if _is_live2d_model_json(str(json_file)):
            model_files.append(json_file)
    
    if not model_files:
        return None
        
    # 如果有多个，优先选择文件名最短的（通常是主模型文件）
    model_files.sort(key=lambda x: len(x.name))
    return str(model_files[0])


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
        
        # 清理模型按钮
        self.clear_btn = QPushButton("Clear Model")
        self.clear_btn.clicked.connect(self.clearCurrentModel)
        self.clear_btn.setEnabled(False)  # 初始时禁用
        file_layout.addWidget(self.clear_btn)

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

        # 分辨率控制
        resolution_layout = QVBoxLayout()
        resolution_layout.addWidget(QLabel("Resolution:"))
        
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "Auto (Fit Container)",
            "800x600", 
            "1024x768",
            "1280x720", 
            "1920x1080",
            "Custom"
        ])
        self.resolution_combo.currentTextChanged.connect(self.onResolutionChanged)
        resolution_layout.addWidget(self.resolution_combo)
        
        # 自定义分辨率输入
        custom_layout = QHBoxLayout()
        self.width_input = QComboBox()
        self.width_input.setEditable(True)
        self.width_input.addItems(["400", "800", "1024", "1280", "1920"])
        self.width_input.setCurrentText("800")
        
        self.height_input = QComboBox()  
        self.height_input.setEditable(True)
        self.height_input.addItems(["300", "600", "768", "720", "1080"])
        self.height_input.setCurrentText("600")
        
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.applyCustomResolution)
        
        custom_layout.addWidget(QLabel("W:"))
        custom_layout.addWidget(self.width_input)
        custom_layout.addWidget(QLabel("H:"))
        custom_layout.addWidget(self.height_input)
        custom_layout.addWidget(apply_btn)
        
        resolution_layout.addLayout(custom_layout)
        canvas_layout.addLayout(resolution_layout)

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
        """从文件夹加载Live2D模型，带验证和错误恢复"""
        self.current_model_path = folder_path
        self.model_path_label.setText(f"Model Path: {folder_path}")

        # 查找有效的Live2D模型文件
        model_file_path = _find_valid_model_json(folder_path)
        
        if not model_file_path:
            # 没有找到有效的模型文件
            error_msg = "No valid Live2D model file found in the selected folder"
            self.statusChanged.emit(error_msg)
            self.addStatusMessage(f"Error: {error_msg}")
            self.addStatusMessage("Please ensure the folder contains a valid *model*.json file")
            
            # 清理当前状态，但不重置整个界面
            self.clearCurrentModel()
            return

        try:
            # 验证并加载模型数据
            with open(model_file_path, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
                
            # 二次验证JSON结构
            if not isinstance(model_data, dict):
                raise ValueError("Invalid JSON structure: not a dictionary")
                
            file_refs = model_data.get('FileReferences', {})
            if not isinstance(file_refs, dict):
                raise ValueError("Invalid Live2D model: missing or invalid FileReferences")
                
            # 检查必要的文件引用
            moc_file = file_refs.get('Moc')
            if not moc_file or not isinstance(moc_file, str):
                raise ValueError("Invalid Live2D model: missing Moc file reference")

            # 验证成功，保存模型数据
            self.model_data = model_data
            self.model_data['path'] = model_file_path

            # 更新控制界面
            self.updateControlsFromModel()

            # 发送到Web视图
            model_url = QUrl.fromLocalFile(model_file_path).toString()
            self.sendMessageToWeb('loadModel', {
                'modelPath': model_file_path,
                'modelUrl': model_url,
                'modelData': self.model_data
            })

            # 延迟发送画布更新消息，确保模型加载完成
            QTimer.singleShot(200, lambda: self.sendMessageToWeb('updateCanvas', {}))

            self.modelLoaded.emit(model_file_path)
            self.addStatusMessage(f"Successfully loaded model: {Path(model_file_path).name}")
            
            # 启用清理按钮
            self.clear_btn.setEnabled(True)

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON file: {str(e)}"
            self.handleModelLoadError(error_msg, model_file_path)
            
        except ValueError as e:
            error_msg = f"Invalid Live2D model: {str(e)}"
            self.handleModelLoadError(error_msg, model_file_path)
            
        except Exception as e:
            error_msg = f"Failed to load model: {str(e)}"
            self.handleModelLoadError(error_msg, model_file_path)

    def handleModelLoadError(self, error_msg, file_path=None):
        """处理模型加载错误，提供恢复选项"""
        self.modelLoadFailed.emit(error_msg)
        self.addStatusMessage(f"Error: {error_msg}")
        
        if file_path:
            self.addStatusMessage(f"Problem file: {Path(file_path).name}")
            
        self.addStatusMessage("You can:")
        self.addStatusMessage("1. Select a different folder with valid Live2D model")
        self.addStatusMessage("2. Click 'Clear' to reset the preview")
        
        # 清理当前状态但保持界面可用
        self.clearCurrentModel()

    def clearCurrentModel(self):
        """清理当前模型状态，重置预览器"""
        # 清理模型数据
        self.model_data = {}
        self.current_model_path = None
        
        # 重置控制界面
        self.expression_combo.clear()
        self.expression_combo.addItem("Default")
        self.motion_list.clear()
        
        # 重置Web视图到初始状态
        self.sendMessageToWeb('clearModel', {})
        
        # 更新路径标签
        self.model_path_label.setText("No model selected")
        
        # 禁用清理按钮
        self.clear_btn.setEnabled(False)
        
        self.addStatusMessage("Model cleared. Ready to load new model.")

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

        # 动作 - 优化显示，避免重复
        self.motion_list.clear()
        if 'FileReferences' in self.model_data and 'Motions' in self.model_data['FileReferences']:
            motions = self.model_data['FileReferences']['Motions']
            if isinstance(motions, dict):
                # 按动作组显示，而不是每个文件单独显示
                for category, motion_list in motions.items():
                    if isinstance(motion_list, list) and len(motion_list) > 0:
                        # 显示动作组名和动作数量
                        count = len(motion_list)
                        display_name = f"{category} ({count} motion{'s' if count > 1 else ''})"
                        item = QListWidgetItem(display_name)
                        # 存储动作组名用于播放
                        item.setData(Qt.UserRole, category)
                        # 存储动作数量
                        item.setData(Qt.UserRole + 1, count)
                        self.motion_list.addItem(item)

    def onExpressionChanged(self, expression):
        """表情改变事件"""
        if expression and expression != "Default":
            self.sendMessageToWeb('setExpression', {'expression': expression})
            self.addStatusMessage(f"Switch expression: {expression}")

    def onMotionClicked(self, item):
        """动作点击事件 - 选择动作时立即播放"""
        motion_group = item.data(Qt.UserRole)  # 动作组名
        motion_count = item.data(Qt.UserRole + 1)  # 动作数量
        
        if motion_group:
            # 立即播放选中的动作组（随机选择组内动作）
            self.sendMessageToWeb('playMotion', {'motion': motion_group})
            self.addStatusMessage(f"Playing motion group: {motion_group} ({motion_count} motions available)")
            
            # 高亮显示当前选中的动作
            for i in range(self.motion_list.count()):
                list_item = self.motion_list.item(i)
                if list_item == item:
                    list_item.setSelected(True)
                else:
                    list_item.setSelected(False)

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

    def onResolutionChanged(self, resolution_text):
        """分辨率改变事件"""
        if resolution_text == "Auto (Fit Container)":
            self.sendMessageToWeb('setResolution', {'auto': True})
            self.addStatusMessage("Set resolution to auto-fit")
        elif resolution_text == "Custom":
            # 自定义分辨率，等待用户点击Apply按钮
            pass
        else:
            # 解析预设分辨率
            try:
                width, height = resolution_text.split('x')
                width, height = int(width), int(height)
                self.sendMessageToWeb('setResolution', {'width': width, 'height': height, 'auto': False})
                self.addStatusMessage(f"Set resolution to {width}x{height}")
            except ValueError:
                self.addStatusMessage(f"Invalid resolution format: {resolution_text}")

    def applyCustomResolution(self):
        """应用自定义分辨率"""
        try:
            width = int(self.width_input.currentText())
            height = int(self.height_input.currentText())
            
            if width < 100 or height < 100:
                self.addStatusMessage("Resolution too small (minimum 100x100)")
                return
                
            if width > 4000 or height > 4000:
                self.addStatusMessage("Resolution too large (maximum 4000x4000)")
                return
                
            self.sendMessageToWeb('setResolution', {'width': width, 'height': height, 'auto': False})
            self.addStatusMessage(f"Applied custom resolution: {width}x{height}")
            
        except ValueError:
            self.addStatusMessage("Invalid resolution values")

    def cleanup(self):
        """清理资源（当前为无操作，占位）"""
        pass