import os
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QApplication, QFileDialog
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtGui import QDesktopServices
from qfluentwidgets import SubtitleLabel, PushButton, InfoBar, InfoBarPosition, LineEdit, FluentIcon


class WebPreviewPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('webPreviewPage')  # Required for navigation
        self.current_model_path = None
        self.server_url = None
        self.server_port = None
        
        # 记住上次打开的路径
        self.last_browse_dir = os.path.join(os.getcwd(), "output")  # 默认为项目output目录
        
        self.setupUI()
        self.startWebServer()

    def setupUI(self):
        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        # 标题
        self.title_label = SubtitleLabel("Live2D Web Preview", self)
        self.main_layout.addWidget(self.title_label)
        
        # 描述
        self.desc_label = QLabel(
            "Preview Live2D models in browser without Qt WebEngine dependency.",
            self
        )
        self.desc_label.setWordWrap(True)
        self.main_layout.addWidget(self.desc_label)
        
        # 服务器地址
        self.server_layout = QHBoxLayout()
        self.server_label = SubtitleLabel("Server URL:", self)
        self.server_edit = LineEdit(self)
        self.server_edit.setReadOnly(True)
        self.server_edit.setPlaceholderText("Starting server...")
        self.server_layout.addWidget(self.server_label)
        self.server_layout.addWidget(self.server_edit, 1)
        self.main_layout.addLayout(self.server_layout)
        
        # 打开浏览器按钮
        self.open_browser_btn = PushButton("Open in Browser", self)
        self.open_browser_btn.setIcon(FluentIcon.GLOBE)
        self.open_browser_btn.clicked.connect(self.openInBrowser)
        self.open_browser_btn.setEnabled(False)
        self.main_layout.addWidget(self.open_browser_btn)
        
        # 分隔线
        separator = QFrame(self)
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(separator)
        
        # 模型文件夹选择
        self.model_layout = QHBoxLayout()
        self.model_label = SubtitleLabel("Model Folder:", self)
        self.model_edit = LineEdit(self)
        self.model_edit.setPlaceholderText("Select Live2D model folder...")
        self.model_button = PushButton("Browse", self)
        self.model_button.setIcon(FluentIcon.FOLDER)
        self.model_button.clicked.connect(self.selectModelFolder)
        self.model_layout.addWidget(self.model_label)
        self.model_layout.addWidget(self.model_edit, 1)
        self.model_layout.addWidget(self.model_button)
        self.main_layout.addLayout(self.model_layout)
        
        # 发送到浏览器按钮
        self.load_model_btn = PushButton("Load Model to Browser", self)
        self.load_model_btn.setIcon(FluentIcon.SEND)
        self.load_model_btn.clicked.connect(self.loadModelToPreview)
        self.load_model_btn.setEnabled(False)
        self.main_layout.addWidget(self.load_model_btn)
        
        self.main_layout.addStretch(1)
            
    
    def startWebServer(self):
        """启动Web服务器"""
        try:
            from GUI.web_server import start_server
            
            # 启动服务器
            self.server_port = start_server(host="127.0.0.1", port=0)
            self.server_url = f"http://127.0.0.1:{self.server_port}"
            
            # 更新UI
            self.server_edit.setText(self.server_url)
            self.open_browser_btn.setEnabled(True)
            
            print(f"✅ Web server started: {self.server_url}")
            
            InfoBar.success(
                title="Server Started",
                content=f"Web preview server is running at {self.server_url}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
        except Exception as e:
            print(f"❌ Failed to start web server: {e}")
            self.server_edit.setPlaceholderText("Failed to start server")
            
            InfoBar.error(
                title="Startup Failed",
                content=f"Cannot start web server: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def openInBrowser(self):
        """在浏览器中打开"""
        if self.server_url:
            try:
                QDesktopServices.openUrl(QUrl(self.server_url))
                
                InfoBar.success(
                    title="Success",
                    content="Preview page opened in browser",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            except Exception as e:
                print(f"❌ Failed to open browser: {e}")
                InfoBar.error(
                    title="Failed",
                    content=f"Cannot open browser: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
    
    def selectModelFolder(self):
        """选择模型文件夹"""
        # 使用上次打开的路径，如果不存在则使用项目output目录
        start_dir = self.last_browse_dir if os.path.exists(self.last_browse_dir) else os.getcwd()
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Live2D Model Folder",
            start_dir
        )
        
        if folder:
            self.current_model_path = folder
            self.model_edit.setText(folder)
            self.load_model_btn.setEnabled(True)
            
            # 记住这次打开的路径（使用父目录，方便下次选择同级文件夹）
            self.last_browse_dir = os.path.dirname(folder)
            
            print(f"✅ Model selected: {folder}")

            # 选择后自动尝试发送到浏览器预览
            try:
                self.loadModelToPreview()
            except Exception as e:
                print(f"⚠️ Auto load failed: {e}")
    
    def loadModelToPreview(self):
        """加载模型到预览器"""
        if not self.current_model_path:
            InfoBar.warning(
                title="No Model Selected",
                content="Please select a Live2D model folder first",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        try:
            from GUI.web_server import mount_model_dir
            import requests
            import json
            
            # 挂载模型目录
            base_path = mount_model_dir(self.current_model_path)
            
            # 查找模型JSON文件
            model_json = self.findModelJson(self.current_model_path)
            if not model_json:
                raise Exception("No valid Live2D model JSON found")
            
            # 构建模型URL
            model_filename = os.path.basename(model_json)
            model_url = f"{self.server_url}{base_path}/{model_filename}"

            # 预检：确认模型JSON可访问
            try:
                check = requests.get(model_url, timeout=2)
                if check.status_code != 200:
                    raise Exception(f"Model URL not accessible ({check.status_code})")
            except Exception as e:
                InfoBar.error(
                    title="Model URL Error",
                    content=f"Cannot access model JSON: {model_url}\n{e}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=4000,
                    parent=self
                )
                print(f"❌ Model URL precheck failed: {e}")
                return
            
            # 通过 HTTP API 广播加载模型消息
            broadcast_url = f"{self.server_url}/api/preview/broadcast"
            message = {
                "type": "loadModel",
                "modelUrl": model_url,
                "modelPath": model_url
            }
            
            response = requests.post(broadcast_url, json=message, timeout=2)

            if response.status_code == 200:
                # 尝试读取服务器返回的客户端数量，提示未连接的情况
                try:
                    resp_json = response.json()
                    clients = int(resp_json.get("clients", 0))
                except Exception:
                    clients = 0

                if clients <= 0:
                    InfoBar.warning(
                        title="No Browser Connected",
                        content="Preview page not connected (WS). Opening browser and will retry...",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                    print(f"⚠️ No preview clients connected; model not delivered: {model_url}")
                    # 自动打开浏览器，并在WS连接后进行多次重试广播
                    try:
                        self.openInBrowser()
                    except Exception as e:
                        print(f"⚠️ Failed to open browser automatically: {e}")

                    # 保存用于重试的上下文
                    self._last_model_url = model_url
                    self._last_message_payload = message
                    self._retry_attempts = 3

                    def _retry_once():
                        nonlocal broadcast_url
                        if getattr(self, "_retry_attempts", 0) <= 0:
                            return
                        try:
                            resp = requests.post(broadcast_url, json=self._last_message_payload, timeout=2)
                            ok = False
                            if resp.status_code == 200:
                                try:
                                    data = resp.json()
                                    c = int(data.get("clients", 0))
                                    ok = c > 0
                                except Exception:
                                    ok = False
                            if ok:
                                InfoBar.success(
                                    title="Model Loaded",
                                    content="Model sent to browser preview (auto retry)",
                                    orient=Qt.Horizontal,
                                    isClosable=True,
                                    position=InfoBarPosition.TOP,
                                    duration=2000,
                                    parent=self
                                )
                                print(f"✅ Model loaded after retry: {self._last_model_url}")
                                self._retry_attempts = 0
                                return
                            else:
                                self._retry_attempts -= 1
                                print(f"⏳ Retry broadcast, attempts left: {self._retry_attempts}")
                                if self._retry_attempts > 0:
                                    QTimer.singleShot(1200, _retry_once)
                        except Exception as e:
                            self._retry_attempts -= 1
                            print(f"❌ Retry broadcast error: {e}")
                            if self._retry_attempts > 0:
                                QTimer.singleShot(1200, _retry_once)

                    # 启动第一次重试
                    QTimer.singleShot(1200, _retry_once)
                    return

                InfoBar.success(
                    title="Model Loaded",
                    content="Model sent to browser preview successfully",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                print(f"✅ Model loaded: {model_url}")
            else:
                raise Exception(f"Server error: {response.status_code}")
        
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            InfoBar.error(
                title="Load Failed",
                content=f"Cannot load model: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def findModelJson(self, folder):
        """在文件夹中查找模型JSON文件
        
        支持的格式：
        - *.model3.json (Live2D Cubism 3.0+)
        - *.model.json (Live2D Cubism 2.1)
        - *model*.json (任何包含"model"的json文件)
        """
        import json
        
        # 优先级1: 标准的 .model3.json 文件
        for file in os.listdir(folder):
            if file.endswith('.model3.json'):
                json_path = os.path.join(folder, file)
                if self._validate_model_json(json_path):
                    return json_path
        
        # 优先级2: 标准的 .model.json 文件
        for file in os.listdir(folder):
            if file.endswith('.model.json'):
                json_path = os.path.join(folder, file)
                if self._validate_model_json(json_path):
                    return json_path
        
        # 优先级3: 任何包含"model"并以.json结尾的文件
        for file in os.listdir(folder):
            if 'model' in file.lower() and file.endswith('.json'):
                json_path = os.path.join(folder, file)
                if self._validate_model_json(json_path):
                    return json_path
        
        # 优先级4: 尝试所有.json文件（作为最后的后备）
        for file in os.listdir(folder):
            if file.endswith('.json'):
                json_path = os.path.join(folder, file)
                if self._validate_model_json(json_path):
                    return json_path
        
        return None
    
    def _validate_model_json(self, json_path):
        """验证JSON文件是否为有效的Live2D模型文件"""
        try:
            import json
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                return False
            
            fr = data.get('FileReferences')
            if isinstance(fr, dict) and isinstance(fr.get('Moc'), str):
                return True
            if isinstance(data.get('model'), str) and isinstance(data.get('textures'), list):
                return True
            return False
            
        except Exception as e:
            print(f"⚠️ Failed to validate {json_path}: {e}")
            return False
    
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
