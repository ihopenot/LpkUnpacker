import os
import sys
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
    QListWidget, QListWidgetItem, QGroupBox, QSplitter
)
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QTimer
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
    WEB_ENGINE_AVAILABLE = True
except Exception:
    QWebEngineView = None
    QWebEngineSettings = None
    WEB_ENGINE_AVAILABLE = False
from PyQt5.QtGui import QFont, QDesktopServices
from qfluentwidgets import (
    PushButton, ComboBox, TextEdit, Slider, BodyLabel, SubtitleLabel, CardWidget, LineEdit
)


def _detect_model_type(file_path: str) -> str:
    """检测模型类型并返回类型名称
    
    Returns:
        "live2d_v3": Live2D Cubism 3.0+ (使用 .moc3 文件)
        "live2d_v2": Live2D Cubism 2.1 (使用 .moc 文件)
        "live2d_v1": Live2D v1.x (老版本，使用 .moc 文件)
        "honkai_spine": 崩坏系列游戏格式 (Spine-like)
        "unknown": 未知格式
    """
    try:
        file_name = os.path.basename(file_path).lower()
        if not file_name.endswith('.json'):
            return "unknown"
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not isinstance(data, dict):
            return "unknown"
        
        # 检查是否为崩坏系列游戏格式（Spine-like）
        if 'skeleton' in data and 'atlases' in data:
            return "honkai_spine"
        
        # 检查 Live2D Cubism 3.0+ 模型 (使用 .moc3)
        file_refs = data.get('FileReferences', {})
        if isinstance(file_refs, dict):
            moc = file_refs.get('Moc', '')
            if isinstance(moc, str):
                if moc.lower().endswith('.moc3'):
                    return "live2d_v3"
                elif moc.lower().endswith('.moc'):
                    # Cubism 3.0+ 的老版本可能也用 .moc，通过 Version 字段区分
                    version = data.get('Version', 0)
                    if version >= 3:
                        return "live2d_v3"
                    else:
                        return "live2d_v2"
        
        # 检查 Live2D Cubism 2.1 模型 (使用 .moc)
        # v2 的特征：有 model 字段指向 .moc 文件
        model_file = data.get('model', '')
        if isinstance(model_file, str) and model_file.lower().endswith('.moc'):
            return "live2d_v2"
        
        # 检查是否有 textures 或 motions 字段 (Live2D 的通用特征)
        if 'textures' in data or 'motions' in data:
            # 尝试通过其他字段判断版本
            if 'model' in data:
                return "live2d_v2"  # 老版本格式
            elif 'FileReferences' in data:
                return "live2d_v3"  # 新版本格式
            else:
                return "live2d_v1"  # 可能是 v1 版本
            
        return "unknown"
        
    except Exception as e:
        print(f"Error detecting model type: {e}")
        return "unknown"


def _is_live2d_model_json(file_path: str) -> bool:
    """验证是否为有效的Live2D模型JSON文件
    
    支持的版本：
    - Live2D Cubism 3.0+ (v3, v4)
    - Live2D Cubism 2.1 (v2)
    - Live2D v1.x (有限支持，取决于运行时库)
    """
    model_type = _detect_model_type(file_path)
    return model_type in ["live2d_v1", "live2d_v2", "live2d_v3"]


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
        self.proxy_port = None
        self._mounted_base = None
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

        self.select_folder_btn = PushButton("Select Model Folder")
        self.select_folder_btn.clicked.connect(self.selectModelFolder)
        file_layout.addWidget(self.select_folder_btn)
        
        # 清理模型按钮
        self.clear_btn = PushButton("Clear Model")
        self.clear_btn.clicked.connect(self.clearCurrentModel)
        self.clear_btn.setEnabled(False)  # 初始时禁用
        file_layout.addWidget(self.clear_btn)

        self.model_path_label = BodyLabel("No model selected")
        self.model_path_label.setWordWrap(True)
        file_layout.addWidget(self.model_path_label)

        layout.addWidget(file_group)

        # 表情控制区域
        expression_group = QGroupBox("Expression Control")
        expression_layout = QVBoxLayout(expression_group)

        self.expression_combo = ComboBox()
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
        opacity_layout.addWidget(BodyLabel("Opacity:"))
        self.opacity_slider = Slider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.onOpacityChanged)
        self.opacity_label = BodyLabel("100%")
        self.opacity_label.setMinimumWidth(40)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        canvas_layout.addLayout(opacity_layout)

        # 模型旋转
        rotation_layout = QHBoxLayout()
        rotation_layout.addWidget(BodyLabel("Rotation:"))
        self.rotation_slider = Slider(Qt.Horizontal)
        self.rotation_slider.setRange(-180, 180)
        self.rotation_slider.setValue(0)
        self.rotation_slider.valueChanged.connect(self.onRotationChanged)
        self.rotation_label = BodyLabel("0°")
        self.rotation_label.setMinimumWidth(40)
        rotation_layout.addWidget(self.rotation_slider)
        rotation_layout.addWidget(self.rotation_label)
        canvas_layout.addLayout(rotation_layout)

        # 分辨率控制
        resolution_layout = QVBoxLayout()
        resolution_layout.addWidget(BodyLabel("Resolution:"))
        
        self.resolution_combo = ComboBox()
        self.resolution_combo.addItems([
            "Auto (Fit Container)",
            "800x600", 
            "1024x768",
            "1280x720", 
            "1920x1080",
            "2560x1440",
            "3840x2160",
            "Custom"
        ])
        self.resolution_combo.currentTextChanged.connect(self.onResolutionChanged)
        resolution_layout.addWidget(self.resolution_combo)
        
        # 自定义分辨率输入
        custom_layout = QHBoxLayout()
        self.width_input = LineEdit()
        self.width_input.setPlaceholderText("Width")
        self.width_input.setText("800")
        self.width_input.setFixedWidth(80)
        
        self.height_input = LineEdit()
        self.height_input.setPlaceholderText("Height")
        self.height_input.setText("600")
        self.height_input.setFixedWidth(80)
        
        apply_btn = PushButton("Apply")
        apply_btn.clicked.connect(self.applyCustomResolution)
        
        custom_layout.addWidget(BodyLabel("W:"))
        custom_layout.addWidget(self.width_input)
        custom_layout.addWidget(BodyLabel("H:"))
        custom_layout.addWidget(self.height_input)
        custom_layout.addWidget(apply_btn)
        
        resolution_layout.addLayout(custom_layout)
        canvas_layout.addLayout(resolution_layout)

        layout.addWidget(canvas_group)

        # 背景设置区域
        bg_group = QGroupBox("Background Settings")
        bg_layout = QVBoxLayout(bg_group)

        self.transparent_bg_btn = PushButton("Transparent Background")
        self.transparent_bg_btn.setCheckable(True)
        self.transparent_bg_btn.setChecked(True)
        self.transparent_bg_btn.clicked.connect(self.onBackgroundChanged)
        bg_layout.addWidget(self.transparent_bg_btn)

        self.colored_bg_btn = PushButton("Colored Background")
        self.colored_bg_btn.setCheckable(True)
        self.colored_bg_btn.clicked.connect(self.onBackgroundChanged)
        bg_layout.addWidget(self.colored_bg_btn)

        layout.addWidget(bg_group)

        # 状态信息
        status_group = QGroupBox("Status Information")
        status_layout = QVBoxLayout(status_group)

        self.status_text = TextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)

        layout.addWidget(status_group)

        # 浏览器预览（在开发与打包环境都可用）
        preview_group = QGroupBox("Web Preview")
        preview_layout = QVBoxLayout(preview_group)

        self.open_browser_btn = PushButton("Open Preview in Browser")
        self.open_browser_btn.clicked.connect(self.openPreviewInBrowser)
        preview_layout.addWidget(self.open_browser_btn)

        layout.addWidget(preview_group)

        layout.addStretch()
        return panel

    def createPreviewPanel(self):
        """创建右侧预览面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Web视图（可选）
        self.web_view = None
        if WEB_ENGINE_AVAILABLE:
            try:
                self.web_view = QWebEngineView()
                # 允许本地HTML访问远程CDN与本地文件URL
                settings = self.web_view.settings()
                settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
                settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
                self.web_view.setMinimumSize(400, 400)
                layout.addWidget(self.web_view)
            except Exception as e:
                print(f"Warn: failed to init QWebEngineView - {e}")
                self.web_view = None
        else:
            # 无 Web 引擎时，右侧仅显示占位提示，避免崩溃
            placeholder = BodyLabel("Web preview is unavailable in this build.\nUse the 'Open Preview in Browser' button to view.")
            placeholder.setWordWrap(True)
            layout.addWidget(placeholder)

        return panel

    def setupWebContent(self):
        """设置Web内容（加载静态HTML或在打包环境下使用URL代理）"""
        # 优先尝试使用本地FastAPI代理（在打包与开发环境皆可），避免 file:// 资源加载问题
        try:
            from GUI.web_server import start_server
            port = start_server(host='127.0.0.1', port=0)
            self.proxy_port = port
            # 嵌入式视图使用精简版 index.html（无控制面板）
            proxy_url = f"http://127.0.0.1:{port}/static/live2d/index.html"
            print(f"使用URL代理: {proxy_url}")
            if self.web_view:
                self.web_view.setUrl(QUrl(proxy_url))
            self.statusChanged.emit(f"Using URL proxy at {proxy_url}")
            return
        except Exception as e:
            print(f"启动URL代理失败，回退到本地文件: {e}")
            # 回退到本地文件加载

        # 非打包环境或代理失败，按原逻辑加载本地文件
        if not self.web_view:
            # 无 Web 引擎，跳过嵌入式预览
            self.statusChanged.emit("WebEngine not available, skipping embedded preview.")
            return
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
        if self.web_view:
            self.web_view.load(QUrl.fromLocalFile(str(assets_path.resolve())))

    def openPreviewInBrowser(self):
        """开发环境下：启动FastAPI代理并在系统浏览器打开预览页面"""
        try:
            from GUI.web_server import start_server
        except Exception as e:
            self.addStatusMessage("FastAPI/uvicorn not available. Please run: pip install fastapi uvicorn")
            return

        if not self.proxy_port:
            try:
                self.proxy_port = start_server(host='127.0.0.1', port=0)
                self.addStatusMessage(f"Started web proxy on 127.0.0.1:{self.proxy_port}")
            except Exception as e:
                self.addStatusMessage(f"Failed to start web proxy: {e}")
                return

        # 如果已有选中的模型文件夹，挂载并通过 URL 参数传入
        query = ""
        if self.current_model_path:
            try:
                from GUI.web_server import mount_model_dir
                base = mount_model_dir(self.current_model_path)
                self._mounted_base = base
                # 推断模型入口 JSON 文件
                model_json = Path(self.model_data.get('path') or '').name if self.model_data else ''
                if not model_json:
                    # 在文件夹中寻找一个包含 'model' 的 json
                    candidates = list(Path(self.current_model_path).glob("*model*.json"))
                    if candidates:
                        model_json = candidates[0].name
                if model_json:
                    query = f"?modelBase={base}&modelJson={model_json}"
            except Exception as e:
                self.addStatusMessage(f"Failed to mount model dir for browser preview: {e}")

        url = f"http://127.0.0.1:{self.proxy_port}/static/live2d/web.html{query}"
        QDesktopServices.openUrl(QUrl(url))
        self.addStatusMessage(f"Opened browser preview: {url}")

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
        # 若嵌入式 Web 视图可用但代理未启动，尝试懒启动以确保通过 HTTP 加载资源
        if self.web_view and not self.proxy_port:
            try:
                from GUI.web_server import start_server
                self.proxy_port = start_server(host='127.0.0.1', port=0)
                # 嵌入式视图仍使用 index.html
                proxy_url = f"http://127.0.0.1:{self.proxy_port}/static/live2d/index.html"
                self.web_view.setUrl(QUrl(proxy_url))
                self.addStatusMessage(f"Started web proxy for embedded view: {proxy_url}")
            except Exception as e:
                self.addStatusMessage(f"Failed to start embedded web proxy: {e}")
                # 继续尝试本地文件方案

        self.current_model_path = folder_path
        self.model_path_label.setText(f"Model Path: {folder_path}")

        # 查找有效的Live2D模型文件
        model_file_path = _find_valid_model_json(folder_path)
        
        if not model_file_path:
            # 没有找到有效的模型文件，检查是否是其他格式
            folder = Path(folder_path)
            all_json_files = list(folder.glob("*.json"))
            
            # 检测其他格式
            detected_types = {}
            for json_file in all_json_files:
                model_type = _detect_model_type(str(json_file))
                if model_type != "unknown":
                    detected_types[str(json_file)] = model_type
                
                if model_type == "honkai_spine":
                    error_msg = "Detected Honkai/Spine format model (not Live2D Cubism)"
                    self.statusChanged.emit(error_msg)
                    self.addStatusMessage(f"⚠️ {error_msg}")
                    self.addStatusMessage(f"Found: {json_file.name}")
                    self.addStatusMessage("This format is NOT supported by Live2D preview.")
                    self.addStatusMessage("")
                    self.addStatusMessage("📌 Supported formats:")
                    self.addStatusMessage("  • Live2D Cubism v3/v4 (.moc3 files)")
                    self.addStatusMessage("  • Live2D Cubism v2 (.moc files)")
                    self.addStatusMessage("  • Live2D v1.x (limited support)")
                    self.addStatusMessage("")
                    self.addStatusMessage("💡 Tip: This appears to be a Honkai series game model")
                    self.addStatusMessage("   which uses Spine or similar animation system.")
                    self.clearCurrentModel()
                    return
            
            # 没有找到任何可识别的模型文件
            error_msg = "No valid Live2D model file found in the selected folder"
            self.statusChanged.emit(error_msg)
            self.addStatusMessage(f"❌ Error: {error_msg}")
            self.addStatusMessage("")
            self.addStatusMessage("📌 Supported Live2D formats:")
            self.addStatusMessage("  • Live2D Cubism v3/v4: *model*.json + .moc3 file")
            self.addStatusMessage("  • Live2D Cubism v2: *model*.json + .moc file")
            self.addStatusMessage("  • Live2D v1.x: *model*.json (legacy)")
            self.addStatusMessage("")
            if detected_types:
                self.addStatusMessage("🔍 Detected files in folder:")
                for file_path, ftype in detected_types.items():
                    fname = Path(file_path).name
                    self.addStatusMessage(f"  • {fname}: {ftype}")
            else:
                self.addStatusMessage("💡 Tip: Make sure the model folder contains:")
                self.addStatusMessage("  - A JSON file with 'model' in its name")
                self.addStatusMessage("  - The corresponding .moc or .moc3 file")
                self.addStatusMessage("  - Texture files (.png)")
            
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

            # 发送到Web视图（优先使用HTTP路径，如果代理可用）
            http_model_url = None
            if self.proxy_port:
                try:
                    from GUI.web_server import mount_model_dir
                    base = mount_model_dir(self.current_model_path)
                    self._mounted_base = base
                    http_model_url = f"http://127.0.0.1:{self.proxy_port}{base}/{Path(model_file_path).name}"
                except Exception as e:
                    self.addStatusMessage(f"Failed to mount model dir: {e}")

            model_url = QUrl.fromLocalFile(model_file_path).toString()
            payload = {
                'modelPath': model_file_path,
                'modelUrl': http_model_url or model_url,
                'modelData': self.model_data
            }
            if http_model_url:
                payload['pathBase'] = self._mounted_base
                payload['httpModelUrl'] = http_model_url
            self.sendMessageToWeb('loadModel', payload)

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
        # 同步广播到外部浏览器预览（通过本地代理）
        try:
            if self.proxy_port:
                import json as _json
                import urllib.request as _ureq
                payload = _json.dumps({"type": msg_type, **data}).encode('utf-8')
                req = _ureq.Request(
                    f"http://127.0.0.1:{self.proxy_port}/api/preview/broadcast",
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                _ureq.urlopen(req, timeout=1.5)
        except Exception as e:
            # 失败不影响本地嵌入式预览
            try:
                self.addStatusMessage(f"Broadcast failed: {e}")
            except Exception:
                pass

        if not self.web_view:
            # 在无 WebEngine 的构建中不执行嵌入式 JS 注入
            return
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
            width = int(self.width_input.text())
            height = int(self.height_input.text())
            
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