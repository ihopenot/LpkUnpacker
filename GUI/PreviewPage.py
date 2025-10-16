import os

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QSizePolicy, QFileDialog, QWidget, QSplitter
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QColor
from qfluentwidgets import (SubtitleLabel, BodyLabel, PushButton, Slider, CheckBox, SpinBox, InfoBar, InfoBarPosition,
                           CardWidget, ColorDialog, SingleDirectionScrollArea, TextBrowser)

from GUI.Live2DPreviewWindow import Live2DPreviewWindow

class DragDropArea(QFrame):
    """拖拽区域组件"""
    fileDropped = pyqtSignal(str)  # 文件拖拽信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.browse_btn = None
        self.setAcceptDrops(True)
        self.setupUI()

    def setupUI(self):
        """设置拖拽区域UI"""
        self.setMinimumHeight(200)
        self.setStyleSheet("""
            DragDropArea {
                border: 2px dashed #ccc;
                border-radius: 10px;
                background: transparent;
            }
            DragDropArea:hover {
                border-color: #007ACC;
                background-color: transparent;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # 拖拽图标（使用文字代替）
        icon_label = SubtitleLabel("📁", self)
        icon_label.setAlignment(Qt.AlignCenter)

        # 主要提示文字
        main_text = SubtitleLabel("Drag & Drop Live2D model files here", self)
        main_text.setAlignment(Qt.AlignCenter)

        # 次要提示文字
        sub_text = BodyLabel("Supported: .moc3, .model3.json files", self)
        sub_text.setAlignment(Qt.AlignCenter)

        # 额外提示文字
        browse_text = BodyLabel("Or click to browse files", self)
        browse_text.setAlignment(Qt.AlignCenter)

        # 浏览文件按钮
        self.browse_btn = PushButton("Browse Files", self)
        self.browse_btn.clicked.connect(self.browse_files)

        layout.addWidget(icon_label)
        layout.addWidget(main_text)
        layout.addWidget(sub_text)
        layout.addWidget(browse_text)
        layout.addWidget(self.browse_btn)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            # 检查是否为Live2D模型文件
            urls = event.mimeData().urls()
            if urls and len(urls) == 1:
                file_path = urls[0].toLocalFile().lower()
                if file_path.endswith('.moc3') or file_path.endswith('.model3.json'):
                    event.acceptProposedAction()
                    self.setStyleSheet("""
                        DragDropArea {
                            border: 2px solid #007ACC;
                            border-radius: 10px;
                            background-color: transparent;
                        }
                    """)
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        """拖拽离开事件"""
        self.setStyleSheet("""
            DragDropArea {
                border: 2px dashed #ccc;
                border-radius: 10px;
                background-color: transparent;
            }
            DragDropArea:hover {
                border-color: #007ACC;
                background-color: transparent;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        """文件拖拽事件"""
        urls = event.mimeData().urls()
        if urls and len(urls) == 1:
            file_path = urls[0].toLocalFile()
            file_path_lower = file_path.lower()
            if (file_path_lower.endswith('.moc3') or file_path_lower.endswith('.model3.json')) and os.path.exists(file_path):
                self.fileDropped.emit(file_path)
                event.acceptProposedAction()

        # 恢复样式
        self.dragLeaveEvent(event)

    def browse_files(self):
        """浏览文件对话框"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Live2D Model File",
            "",
            "Live2D Model Files (*.moc3 *.model3.json);;MOC3 Files (*.moc3);;Model3 JSON Files (*.model3.json);;All Files (*)"
        )

        if file_path and os.path.exists(file_path):
            self.fileDropped.emit(file_path)

class Live2DSettingsPanel(QFrame):
    """Live2D设置面板"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.preview_window = None

        self.width_spinbox = None
        self.height_spinbox = None
        self.opacity_label = None
        self.opacity_slider = None
        # self.stay_on_top_check = None
        self.show_controls_check = None

        self.scale_label = None
        self.scale_slider = None
        self.position_x_spinbox = None
        self.position_y_spinbox = None
        self.bg_transparent_check = None
        # 按钮与颜色展示
        self.bg_color_btn = None
        self.bg_color_preview = None
        self.selected_bg_color = QColor(255, 255, 255)

        self.mouse_tracking_check = None
        self.auto_blink_check = None
        self.auto_breath_check = None
        self.sensitivity_label = None
        self.sensitivity_slider = None

        self.setupUI()

    def setupUI(self):
        """设置面板UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 20, 0)
        layout.setSpacing(15)

        # 创建滚动区域
        scroll = SingleDirectionScrollArea(orient=Qt.Vertical)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # 窗口设置组
        window_group = self.create_window_settings_group()
        scroll_layout.addWidget(window_group)

        # 模型设置组
        model_group = self.create_model_settings_group()
        scroll_layout.addWidget(model_group)

        # 交互设置组
        interaction_group = self.create_interaction_settings_group()
        scroll_layout.addWidget(interaction_group)

        # 添加弹性空间
        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        scroll.enableTransparentBackground()
        layout.addWidget(scroll)

    def create_window_settings_group(self):
        """创建窗口设置组"""
        group = CardWidget(self)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(15, 15, 15, 15)

        # 组标题
        group_title = SubtitleLabel("Preview Window Settings", group)
        layout.addWidget(group_title)

        # 窗口大小设置
        size_layout = QHBoxLayout()
        size_layout.addWidget(BodyLabel("Window Size:", group))

        self.width_spinbox = SpinBox(group)
        self.width_spinbox.setRange(200, 1920)
        self.width_spinbox.setValue(400)
        self.width_spinbox.setSuffix(" px")

        size_layout.addWidget(BodyLabel("W:", group))
        size_layout.addWidget(self.width_spinbox)

        self.height_spinbox = SpinBox(group)
        self.height_spinbox.setRange(200, 1080)
        self.height_spinbox.setValue(600)
        self.height_spinbox.setSuffix(" px")

        size_layout.addWidget(BodyLabel("H:", group))
        size_layout.addWidget(self.height_spinbox)
        size_layout.addStretch()

        layout.addLayout(size_layout)

        # 模型透明度
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(BodyLabel("Opacity:", group))

        self.opacity_slider = Slider(Qt.Horizontal, group)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(100)

        self.opacity_label = BodyLabel("100%", group)
        self.opacity_label.setMinimumWidth(40)

        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_label.setText(f"{v}%")
        )

        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)

        layout.addLayout(opacity_layout)

        self.show_controls_check = CheckBox("Show control panel by default", group)
        layout.addWidget(self.show_controls_check)

        return group

    def create_model_settings_group(self):
        """创建模型设置组"""
        group = CardWidget(self)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(15, 15, 15, 15)

        # 组标题
        group_title = SubtitleLabel("Model Display Settings", group)
        layout.addWidget(group_title)

        # 模型缩放
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(BodyLabel("Model Scale:", group))

        self.scale_slider = Slider(Qt.Horizontal, group)
        self.scale_slider.setRange(50, 200)
        self.scale_slider.setValue(100)

        self.scale_label = BodyLabel("100%", group)
        self.scale_label.setMinimumWidth(40)

        self.scale_slider.valueChanged.connect(
            lambda v: self.scale_label.setText(f"{v}%")
        )

        scale_layout.addWidget(self.scale_slider)
        scale_layout.addWidget(self.scale_label)

        layout.addLayout(scale_layout)

        # 模型位置偏移
        position_layout = QHBoxLayout()
        position_layout.addWidget(BodyLabel("Position Offset:", group))

        position_layout.addWidget(BodyLabel("X:", group))
        self.position_x_spinbox = SpinBox(group)
        self.position_x_spinbox.setRange(-500, 500)
        self.position_x_spinbox.setValue(0)
        self.position_x_spinbox.setSuffix(" px")
        position_layout.addWidget(self.position_x_spinbox)

        position_layout.addWidget(BodyLabel("Y:", group))
        self.position_y_spinbox = SpinBox(group)
        self.position_y_spinbox.setRange(-500, 500)
        self.position_y_spinbox.setValue(0)
        self.position_y_spinbox.setSuffix(" px")
        position_layout.addWidget(self.position_y_spinbox)
        position_layout.addStretch()

        layout.addLayout(position_layout)

        # 背景设置
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(BodyLabel("Background:", group))

        self.bg_transparent_check = CheckBox("Transparent", group)
        self.bg_transparent_check.setChecked(True)
        bg_layout.addWidget(self.bg_transparent_check)

        # 颜色选择按钮
        self.bg_color_btn = PushButton("Select Color", group)
        self.bg_color_btn.setEnabled(False)
        self.bg_color_btn.clicked.connect(self.open_color_dialog)
        bg_layout.addWidget(self.bg_color_btn)

        # 颜色预览块
        self.bg_color_preview = QFrame(group)
        self.bg_color_preview.setFixedSize(24, 24)
        self.bg_color_preview.setStyleSheet(
            f"QFrame{{border:1px solid #ccc; border-radius:4px; background:{self.selected_bg_color.name()};}}"
        )
        bg_layout.addWidget(self.bg_color_preview)

        # 连接透明背景选择框
        self.bg_transparent_check.toggled.connect(
            lambda checked: self.bg_color_btn.setEnabled(not checked)
        )

        bg_layout.addStretch()
        layout.addLayout(bg_layout)

        return group

    def create_interaction_settings_group(self):
        """创建交互设置组"""
        group = CardWidget(self)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(15, 15, 15, 15)

        # 组标题
        group_title = SubtitleLabel("Interaction Settings", group)
        layout.addWidget(group_title)

        # 鼠标交互选项
        self.mouse_tracking_check = CheckBox("Enable mouse tracking", group)
        self.mouse_tracking_check.setChecked(True)
        layout.addWidget(self.mouse_tracking_check)

        self.auto_blink_check = CheckBox("Enable auto blinking animation", group)
        self.auto_blink_check.setChecked(True)
        layout.addWidget(self.auto_blink_check)

        self.auto_breath_check = CheckBox("Enable auto breathing animation", group)
        self.auto_breath_check.setChecked(True)
        layout.addWidget(self.auto_breath_check)

        # 交互灵敏度
        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(BodyLabel("Mouse Sensitivity:", group))

        self.sensitivity_slider = Slider(Qt.Horizontal, group)
        self.sensitivity_slider.setRange(1, 10)
        self.sensitivity_slider.setValue(5)

        self.sensitivity_label = BodyLabel("5", group)
        self.sensitivity_label.setMinimumWidth(20)

        self.sensitivity_slider.valueChanged.connect(
            lambda v: self.sensitivity_label.setText(str(v))
        )

        sensitivity_layout.addWidget(self.sensitivity_slider)
        sensitivity_layout.addWidget(self.sensitivity_label)

        layout.addLayout(sensitivity_layout)

        return group

    def open_color_dialog(self):
        """打开颜色选择器并更新所选颜色"""
        dlg = ColorDialog(self.selected_bg_color, "Choose Background Color", self, enableAlpha=False)
        # 实时更新预览
        dlg.colorChanged.connect(self._update_selected_color)

        if dlg.exec_():
            # 确认后取最终颜色（若无 color 属性则尝试其他兼容属性/方法）
            color = getattr(dlg, 'color', None)

            if isinstance(color, QColor):
                self._update_selected_color(color)

    def _update_selected_color(self, color: QColor):
        self.selected_bg_color = color
        # 更新预览块背景
        self.bg_color_preview.setStyleSheet(
            f"QFrame{{border:1px solid #ccc; border-radius:4px; background:{self.selected_bg_color.name()};}}"
        )

    def get_settings(self):
        """获取当前设置"""
        return {
            'window_size': (self.width_spinbox.value(), self.height_spinbox.value()),
            'opacity': self.opacity_slider.value() / 100.0,
            'show_controls': self.show_controls_check.isChecked(),
            'model_scale': self.scale_slider.value() / 100.0,
            'position_offset': (self.position_x_spinbox.value(), self.position_y_spinbox.value()),
            'transparent_bg': self.bg_transparent_check.isChecked(),
            'bg_color': self.selected_bg_color,
            'mouse_tracking': self.mouse_tracking_check.isChecked(),
            'mouse_drag': self.mouse_drag_check.isChecked(),
            'auto_breath': self.auto_breath_check.isChecked(),
            'sensitivity': self.sensitivity_slider.value()
        }

class PreviewPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_panel = None
        self.preview_btn = None
        self.close_all_btn = None
        self.model_info_text_box = None
        self.drag_drop_area = None
        self.title_label = None
        self.main_layout = None
        self.current_model_path = None
        self.setObjectName('previewPage')  # Required for navigation
        self.preview_windows = []  # 存储打开的预览窗口

        self.setupUI()

        # 响应窗口大小变化
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setupUI(self):
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(10)

        # Title
        self.title_label = SubtitleLabel("Live2D Preview", self)
        self.main_layout.addWidget(self.title_label)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal, self)

        # 左侧：拖拽区域和控制按钮
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 10, 10, 0)
        left_layout.setSpacing(10)

        # 拖拽区域
        self.drag_drop_area = DragDropArea(self)
        self.drag_drop_area.fileDropped.connect(self.on_file_dropped)
        left_layout.addWidget(self.drag_drop_area)

        # 当前模型信息
        self.model_info_text_box = TextBrowser(self)
        self.model_info_text_box.setMarkdown("### No model loaded ✨")

        left_layout.addWidget(self.model_info_text_box)

        # 控制按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(30)
        button_layout.addStretch()
        self.preview_btn = PushButton("Preview Model", self)
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(self.preview_current_model)

        self.close_all_btn = PushButton("Close All Windows", self)
        self.close_all_btn.clicked.connect(self.close_all_preview_windows)

        button_layout.addWidget(self.preview_btn)
        button_layout.addWidget(self.close_all_btn)
        button_layout.addStretch()

        left_layout.addLayout(button_layout)

        left_layout.addStretch()

        # 右侧：设置面板
        self.settings_panel = Live2DSettingsPanel(self)

        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(self.settings_panel)
        splitter.setSizes([250, 450])  # 设置初始比例

        self.main_layout.addWidget(splitter)
        self.main_layout.setStretch(0, 0)
        self.main_layout.setStretch(1, 1)

        # 当前模型路径
        self.current_model_path = None

    def on_file_dropped(self, file_path):
        """处理文件拖拽"""
        if not os.path.exists(file_path):
            self.show_error("File not found", f"The file {file_path} does not exist.")
            return

        # 检查文件扩展名，支持.moc3和.model3.json文件
        file_ext = file_path.lower()
        if not (file_ext.endswith('.moc3') or file_ext.endswith('.model3.json')):
            self.show_error("Invalid file type",
                           "Please select a .moc3 or .model3.json Live2D model file.")
            return

        # 更新当前模型
        self.current_model_path = file_path

        # 显示模型信息
        model_name = os.path.basename(file_path)
        model_dir = os.path.dirname(file_path)

        info_text = f"""### Model Loaded ✨

**File:** `{model_name}`

**Directory:** `{model_dir}`

**Type:** {'Live2D Model v3 (.moc3)' if file_ext.endswith('.moc3') else 'Live2D Config (.model3.json)'}

Ready to preview! 🚀"""

        self.model_info_text_box.setMarkdown(info_text)
        self.preview_btn.setEnabled(True)

        # 显示成功信息
        InfoBar.success(
            title="Model Loaded",
            content=f"Successfully loaded: {model_name}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def preview_current_model(self):
        """预览当前模型"""
        if not self.current_model_path:
            self.show_error("No model selected", "Please drag and drop a .moc3 file first.")
            return

        # 获取设置
        settings = self.settings_panel.get_settings()

        # 创建预览窗口
        preview_window = Live2DPreviewWindow(self.current_model_path, self)

        # 应用设置
        preview_window.apply_settings(settings)

        # 显示控制面板
        if settings['show_controls']:
            preview_window.toggle_control_panel()

        # 连接关闭信号
        preview_window.closed.connect(lambda: self.on_preview_window_closed(preview_window))

        # 添加到窗口列表并显示
        self.preview_windows.append(preview_window)
        preview_window.show()

    def on_preview_window_closed(self, window):
        """预览窗口关闭处理"""
        if window in self.preview_windows:
            self.preview_windows.remove(window)

    def close_all_preview_windows(self):
        """关闭所有预览窗口"""
        for window in self.preview_windows[:]:  # 创建副本避免修改列表时出错
            window.close()
        self.preview_windows.clear()

    def show_error(self, title, message):
        """显示错误信息"""
        InfoBar.error(
            title=title,
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
