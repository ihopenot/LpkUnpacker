import os
import re
import json

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QFileDialog, QWidget, QSplitter
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QCoreApplication
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QColor
from qfluentwidgets import (SubtitleLabel, BodyLabel, PushButton, Slider, CheckBox, SpinBox, InfoBar, InfoBarPosition,
                           CardWidget, SingleDirectionScrollArea, TextBrowser, ColorDialog)

from GUI.Live2DPreviewWindow import Live2DPreviewWindow

# Helper to check *model*.json pattern
_def_model_json_pattern = re.compile(r"model\d+\.json$", re.IGNORECASE)

def _is_model_json(path: str) -> bool:
    try:
        return bool(_def_model_json_pattern.search(path or ""))
    except Exception:
        return False

# --- Live2D v3 model json helpers ---

def _is_live2d_v3_json(data: dict) -> bool:
    try:
        if not isinstance(data, dict):
            return False
        # Common v3 structure: FileReferences with Moc ending in .moc3
        refs = data.get('FileReferences') or {}
        if isinstance(refs, dict):
            moc = refs.get('Moc')
            if isinstance(moc, str) and moc.lower().endswith('.moc3'):
                return True
        # Optional: Version >= 3
        ver = data.get('Version')
        if isinstance(ver, int) and ver == 3:
            return True
    except Exception:
        return False
    return False

def _prepare_and_validate_model_json(path: str):
    """
    Validate Live2D v3 model json and pretty-print if needed.
    Returns (safe_path, temp_created_path or None).
    Raises Exception on validation failure.
    """
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    data = json.loads(text)
    if not _is_live2d_v3_json(data):
        raise ValueError("Not a valid Live2D v3 model json (missing FileReferences.Moc .moc3)")
    # Pretty-print to same directory to preserve relative paths
    base_dir = os.path.dirname(path)
    base_name = os.path.basename(path)
    name, ext = os.path.splitext(base_name)
    pretty_name = f"{name}.pretty{ext or '.json'}"
    pretty_path = os.path.join(base_dir, pretty_name)
    if os.path.exists(pretty_path):
        idx = 1
        while True:
            alt = os.path.join(base_dir, f"{name}.pretty{idx}{ext or '.json'}")
            if not os.path.exists(alt):
                pretty_path = alt
                break
            idx += 1
    with open(pretty_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    return pretty_path

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

        # 拖拽图标
        icon_label = SubtitleLabel("📁", self)
        icon_label.setAlignment(Qt.AlignCenter)

        # 主要提示文字
        main_text = SubtitleLabel("Drag & Drop Live2D model files here", self)
        main_text.setAlignment(Qt.AlignCenter)

        # 次要提示文字
        sub_text = BodyLabel("Supported: *model*.json files", self)
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
                file_path = urls[0].toLocalFile()
                if _is_model_json(file_path):
                    event.acceptProposedAction()
                    self.setStyleSheet("""
                        #dragDropArea {
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
            #dragDropArea {
                border: 2px dashed #ccc;
                border-radius: 10px;
                background-color: transparent;
            }
            #dragDropArea:hover {
                border-color: #007ACC;
                background-color: transparent;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        """文件拖拽事件"""
        urls = event.mimeData().urls()
        if urls and len(urls) == 1:
            file_path = urls[0].toLocalFile()
            if _is_model_json(file_path) and os.path.exists(file_path):
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
            "Live2D Model Files (*model*.json);;All Files (*)"
        )

        if file_path and os.path.exists(file_path):
            # 严格校验是否为 *model*.json
            if _is_model_json(file_path):
                self.fileDropped.emit(file_path)
            else:
                InfoBar.warning(
                    title="Invalid file type",
                    content="Please select a *model*.json Live2D model file.",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2500,
                    parent=self
                )

class Live2DSettingsPanel(QFrame):
    """Live2D设置面板"""

    settingsChanged = pyqtSignal(dict)
    requestRefreshParams = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.preview_window = None

        self.width_spinbox = None
        self.height_spinbox = None
        self.opacity_label = None
        self.opacity_slider = None
        self.show_controls_check = None

        self.rotation_label = None
        self.rotation_slider = None
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

        # 高级参数控件（动态）
        self.advanced_enable_check = None
        self.advanced_param_sliders = {}  # id -> (slider, label, scale)
        self.PARAM_SPECS = []
        self.param_specs_by_id = {}  # id -> spec dict
        self.advanced_group = None
        self.adv_params_container = None
        self.adv_params_container_layout = None

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

        # 高级设置组（动态构建）
        advanced_group = self.create_advanced_settings_group()
        self.advanced_group = advanced_group
        scroll_layout.addWidget(advanced_group)

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
        self.height_spinbox.setValue(300)
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
        # 实时应用设置
        self.opacity_slider.valueChanged.connect(lambda _: self._emit_settings())

        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)

        layout.addLayout(opacity_layout)

        self.show_controls_check = CheckBox("Show control panel by default", group)
        layout.addWidget(self.show_controls_check)

        # 尺寸变化时也应用
        self.width_spinbox.valueChanged.connect(lambda _: self._emit_settings())
        self.height_spinbox.valueChanged.connect(lambda _: self._emit_settings())

        return group

    def create_model_settings_group(self):
        """创建模型设置组"""
        group = CardWidget(self)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(15, 15, 15, 15)

        # 组标题
        group_title = SubtitleLabel("Model Display Settings", group)
        layout.addWidget(group_title)

        # 模型旋转
        rotation_layout = QHBoxLayout()
        rotation_layout.addWidget(BodyLabel("Model Rotation:", group))

        self.rotation_slider = Slider(Qt.Horizontal, group)
        self.rotation_slider.setRange(0, 360)
        self.rotation_slider.setValue(0)

        self.rotation_label = BodyLabel("0°", group)
        self.rotation_label.setMinimumWidth(40)

        self.rotation_slider.valueChanged.connect(
            lambda v: self.rotation_label.setText(f"{v}°")
        )
        # 实时应用旋转
        self.rotation_slider.valueChanged.connect(lambda _: self._emit_settings())

        rotation_layout.addWidget(self.rotation_slider)
        rotation_layout.addWidget(self.rotation_label)

        layout.addLayout(rotation_layout)

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
        # 透明背景切换时也应用设置
        self.bg_transparent_check.toggled.connect(lambda _: self._emit_settings())

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

        # 交互选项
        self.mouse_tracking_check = CheckBox("Enable mouse tracking", group)
        self.mouse_tracking_check.setChecked(True)
        self.mouse_tracking_check.clicked.connect(lambda _: self._emit_settings())
        layout.addWidget(self.mouse_tracking_check)

        self.auto_blink_check = CheckBox("Enable auto blinking animation", group)
        self.auto_blink_check.setChecked(True)
        self.auto_blink_check.clicked.connect(lambda _: self._emit_settings())
        layout.addWidget(self.auto_blink_check)

        self.auto_breath_check = CheckBox("Enable auto breathing animation", group)
        self.auto_breath_check.setChecked(True)
        self.auto_breath_check.clicked.connect(lambda _: self._emit_settings())
        layout.addWidget(self.auto_breath_check)

        return group

    def create_advanced_settings_group(self):
        """创建高级设置组的容器；具体参数根据模型动态生成"""
        group = CardWidget(self)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(15, 15, 15, 15)

        title = SubtitleLabel("Advanced Settings", group)
        layout.addWidget(title)

        self.advanced_enable_check = CheckBox("Enable advanced parameter overrides", group)
        self.advanced_enable_check.setChecked(False)
        self.advanced_enable_check.toggled.connect(lambda _: self._emit_settings())
        layout.addWidget(self.advanced_enable_check)

        # 容器用于放置动态参数滑条
        self.adv_params_container = QWidget(group)
        self.adv_params_container_layout = QVBoxLayout(self.adv_params_container)
        self.adv_params_container_layout.setContentsMargins(0, 0, 0, 0)
        self.adv_params_container_layout.setSpacing(8)
        layout.addWidget(self.adv_params_container)

        # Buttons row (adv params)
        btns_layout = QHBoxLayout()
        refresh_btn = PushButton("Refresh From Current Model", group)
        refresh_btn.clicked.connect(self.requestRefreshParams.emit)
        reset_btn = PushButton("Reset Advanced Params", group)
        reset_btn.clicked.connect(self.reset_advanced_params)
        btns_layout.addWidget(refresh_btn)
        btns_layout.addWidget(reset_btn)
        btns_layout.addStretch()
        layout.addLayout(btns_layout)

        return group

    def _emit_settings(self):
        try:
            self.settingsChanged.emit(self.get_settings())
        except Exception:
            pass

    def reset_advanced_params(self):
        """将高级参数重置为当前模型的默认值"""
        for spec in self.PARAM_SPECS:
            sid = spec['id']
            if sid in self.advanced_param_sliders:
                slider, _label, scale = self.advanced_param_sliders[sid]
                dv = float(spec.get('default', 0.0))
                dv = max(spec.get('min', dv), min(spec.get('max', dv), dv))
                slider.setValue(int(round(dv * scale)))

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            child = item.layout()
            if child is not None:
                self._clear_layout(child)

    def rebuild_advanced_params(self, meta_list: list):
        """依据模型枚举到的参数元数据动态重建高级设置UI.
        meta: list of {id, type, value, min, max, default}
        尽可能保留用户当前已设定的值。
        """
        # 尽可能保留用户当前已设定的值
        prev_values = {}
        for pid, (slider, _lbl, scale) in self.advanced_param_sliders.items():
            prev_values[pid] = slider.value() / float(scale)

        # 清理旧控件
        self._clear_layout(self.adv_params_container_layout)
        self.advanced_param_sliders.clear()
        self.PARAM_SPECS = []
        self.param_specs_by_id.clear()

        # 缩放决定函数
        def decide_scale(vmin, vmax):
            rng = max(vmax, vmin) - min(vmax, vmin)
            if rng <= 2.0:
                return 100
            return 1

        # 构造控件，按id字母序排列以保持一致性
        for p in sorted(meta_list, key=lambda x: str(x.get('id', ''))):
            pid = str(p.get('id', ''))
            pmin = float(p.get('min', 0.0))
            pmax = float(p.get('max', 1.0))
            pdef = float(p.get('default', 0.0))+0.0
            pval = float(p.get('value', pdef))
            scale = decide_scale(pmin, pmax)
            spec = {
                'label': pid,
                'id': pid,
                'min': pmin,
                'max': pmax,
                'default': pdef,
                'scale': scale,
            }
            self.PARAM_SPECS.append(spec)
            self.param_specs_by_id[pid] = spec

            row = QHBoxLayout()
            name_label = BodyLabel(f"{pid}:", self.adv_params_container)
            row.addWidget(name_label)

            slider = Slider(Qt.Horizontal, self.adv_params_container)
            s_min = int(round(pmin * scale))
            s_max = int(round(pmax * scale))
            # Ensure s_min <= s_max
            if s_min > s_max:
                s_min, s_max = s_max, s_min
            slider.setRange(s_min, s_max)

            # 初始值：如果存在则保留之前的值，否则使用模型默认值/当前值
            init_val = prev_values.get(pid, pval)
            init_val = max(pmin, min(pmax, init_val))
            slider.setValue(int(round(init_val * scale)))

            val_label = BodyLabel(f"{init_val:.2f}" if scale != 1 else f"{int(round(init_val))}", self.adv_params_container)
            val_label.setMinimumWidth(80)

            def make_on_change(lbl, scale_factor):
                return lambda v: lbl.setText(f"{v/scale_factor:.2f}") if scale_factor != 1 else lbl.setText(f"{v}")

            slider.valueChanged.connect(make_on_change(val_label, scale))
            slider.valueChanged.connect(lambda _: self._emit_settings())

            row.addWidget(slider)
            row.addWidget(val_label)
            row.addStretch()

            self.adv_params_container_layout.addLayout(row)
            self.advanced_param_sliders[pid] = (slider, val_label, scale)

    def get_settings(self):
        """获取当前设置"""
        settings = {
            'window_size': (self.width_spinbox.value(), self.height_spinbox.value()),
            'opacity': self.opacity_slider.value() / 100.0,
            'show_controls': self.show_controls_check.isChecked(),
            'model_rotation': self.rotation_slider.value(),
            'transparent_bg': self.bg_transparent_check.isChecked(),
            'bg_color': self.selected_bg_color,
            'mouse_tracking': self.mouse_tracking_check.isChecked(),
            'auto_blink': self.auto_blink_check.isChecked(),
            'auto_breath': self.auto_breath_check.isChecked(),
        }
        # 高级参数
        adv_enabled = bool(self.advanced_enable_check.isChecked()) if self.advanced_enable_check else False
        settings['advanced_enabled'] = adv_enabled
        if adv_enabled:
            advanced_params = {}
            for pid, (slider, _label, scale) in self.advanced_param_sliders.items():
                spec = self.param_specs_by_id.get(pid, None)
                val = slider.value() / float(scale)
                if spec:
                    v = max(spec['min'], min(spec['max'], val))
                else:
                    v = val
                advanced_params[pid] = v
            settings['advanced_params'] = advanced_params
        else:
            settings['advanced_params'] = {}
        return settings

    def open_color_dialog(self):
        """使用 qfluentwidgets 的 ColorDialog 选择背景颜色，并实时应用"""
        current = self.selected_bg_color if isinstance(self.selected_bg_color, QColor) else QColor(255, 255, 255)
        try:
            dlg = ColorDialog(current, "Choose Background Color", self, enableAlpha=False)
        except TypeError:
            dlg = ColorDialog(current, "Choose Background Color", self)
        def on_color_changed(color: QColor):
            if isinstance(color, QColor) and color.isValid():
                self.selected_bg_color = color
                try:
                    self.bg_color_preview.setStyleSheet(
                        f"QFrame{{border:1px solid #ccc; border-radius:4px; background:{color.name()};}}"
                    )
                except Exception:
                    pass
                self._emit_settings()
        try:
            dlg.colorChanged.connect(on_color_changed)
        except Exception:
            pass
        try:
            dlg.exec()
        except Exception:
            pass

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
        self.setObjectName('previewPage')
        self.preview_window = None
        # 新增：预览按钮冷却
        self._preview_cooldown_timer = None
        self._preview_cooldown_ms = 1500  # 冷却时长（毫秒）
        # 新增：记录临时美化的 model json 文件（在新文件载入时清理）
        self._temp_model_json_path = None

        self.setupUI()
        # 应用退出前做一次兜底清理，防止文件句柄未及时释放
        try:
            app = QCoreApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(self._cleanup_temp_model_json)
        except Exception:
            pass

    def setupUI(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(10)

        # 标题
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
        # 修改：接入冷却逻辑
        self.preview_btn.clicked.connect(self._on_preview_clicked)

        self.close_all_btn = PushButton("Close Window", self)
        self.close_all_btn.clicked.connect(self.close_preview_window)

        button_layout.addWidget(self.preview_btn)
        button_layout.addWidget(self.close_all_btn)
        button_layout.addStretch()

        left_layout.addLayout(button_layout)

        left_layout.addStretch()

        # 右侧：设置面板
        self.settings_panel = Live2DSettingsPanel(self)
        # Connect live update signals
        self.settings_panel.settingsChanged.connect(self.on_settings_changed)
        self.settings_panel.requestRefreshParams.connect(self.on_request_refresh_params)

        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(self.settings_panel)
        splitter.setSizes([250, 450])  # 设置初始比例

        self.main_layout.addWidget(splitter)
        self.main_layout.setStretch(0, 0)
        self.main_layout.setStretch(1, 1)

        # 当前模型路径
        self.current_model_path = None

        # 新增：初始化冷却计时器
        self._preview_cooldown_timer = QTimer(self)
        self._preview_cooldown_timer.setSingleShot(True)
        self._preview_cooldown_timer.timeout.connect(self._on_preview_cooldown_end)

    # 新增：预览按钮点击（带冷却）
    def _on_preview_clicked(self):
        # 若处于冷却中，拦截点击并提示
        if self._preview_cooldown_timer and self._preview_cooldown_timer.isActive():
            InfoBar.warning(
                title="Wait",
                content="请稍后再点击预览按钮",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1500,
                parent=self
            )
            return
        # 进入冷却：先禁用按钮
        if self.preview_btn is not None:
            self.preview_btn.setEnabled(False)
            try:
                self.preview_btn.setToolTip("按钮冷却中…")
            except Exception:
                pass
        # 开始冷却计时
        if self._preview_cooldown_timer:
            try:
                self._preview_cooldown_timer.start(self._preview_cooldown_ms)
            except Exception:
                # 兜底：若计时器异常，仍尝试在结束时恢复
                pass
        # 执行原有预览逻辑
        try:
            self.preview_current_model()
        except Exception:
            # 忽略异常，等待冷却结束再恢复按钮
            pass

    # 新增：冷却结束处理
    def _on_preview_cooldown_end(self):
        if self.preview_btn is not None:
            # 冷却结束，仅当存在可预览模型时才启用
            self.preview_btn.setEnabled(bool(self.current_model_path))
            try:
                self.preview_btn.setToolTip("")
            except Exception:
                pass

    def _cleanup_temp_model_json(self):
        """删除上一次创建的临时美化 model json（若存在）。"""
        try:
            if self._temp_model_json_path and os.path.isfile(self._temp_model_json_path):
                os.remove(self._temp_model_json_path)
        except Exception:
            pass

    def on_file_dropped(self, file_path):
        """处理文件拖拽"""
        if not os.path.exists(file_path):
            self.show_error("File not found", f"The file {file_path} does not exist.")
            return

        # 检查文件扩展名，支持*model*.json文件
        file_ext = file_path.lower()
        if not _is_model_json(file_ext):
            self.show_error("Invalid file type",
                           "Please select a *model*.json Live2D model file.")
            return

        # 预处理与校验：确保为 Live2D v3 的 json，生成美化副本
        try:
            safe_path = _prepare_and_validate_model_json(file_path)
        except Exception as e:
            self.show_error("Invalid Live2D model json",
                            f"{os.path.basename(file_path)} is not a valid Live2D v3 model json: {e}")
            return

        # 清理旧的临时文件并保存新的
        self._cleanup_temp_model_json()
        self._temp_model_json_path = safe_path

        # 更新当前模型使用美化后的副本
        self.current_model_path = safe_path

        # 显示模型信息
        model_name = os.path.basename(self.current_model_path)
        model_dir = os.path.dirname(self.current_model_path)

        info_text = f"""### Model Loaded ✨

**File:** `{model_name}`

**Directory:** `{model_dir}`

**Type:** Live2D v3 Config (*model*.json)

Ready to preview! 🚀"""

        self.model_info_text_box.setMarkdown(info_text)
        # 仅在未处于冷却中时启用预览按钮
        if not (self._preview_cooldown_timer and self._preview_cooldown_timer.isActive()):
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
            self.show_error("No model selected", "Please drag and drop a *model*.json file first.")
            return

        # 保证同时仅有一个预览窗口
        if self.preview_window is not None:
            self.close_preview_window()

        # 创建预览窗口
        preview_window = Live2DPreviewWindow(self.current_model_path)

        # 通过预览窗口枚举参数并重建高级设置UI
        try:
            meta = preview_window.live2d_canvas.getParameterMetaList() if preview_window.live2d_canvas else []
            if hasattr(self.settings_panel, 'rebuild_advanced_params'):
                self.settings_panel.rebuild_advanced_params(meta)
            parts = preview_window.live2d_canvas.getPartIds() if preview_window.live2d_canvas else []
            if hasattr(self.settings_panel, 'rebuild_parts_opacity'):
                self.settings_panel.rebuild_parts_opacity(parts)
        except Exception:
            pass

        # 连接关闭信号
        preview_window.closed.connect(lambda: self.on_preview_window_closed(preview_window))

        # 只保存一个窗口并显示
        self.preview_window = preview_window
        preview_window.show()

        # 获取（可能被重建后的）设置并应用
        settings = self.settings_panel.get_settings()
        preview_window.apply_settings(settings)

        # 显示控制面板
        if settings['show_controls']:
            preview_window.toggle_control_panel()

    def on_preview_window_closed(self, window):
        """预览窗口关闭处理"""
        if self.preview_window is window:
            self.preview_window = None

    def close_preview_window(self):
        """关闭当前预览窗口"""
        if self.preview_window is not None:
            try:
                self.preview_window.close()
            except Exception:
                pass
            self.preview_window = None

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

    def on_settings_changed(self, settings: dict):
        """应用更新的设置到打开的预览窗口（实时更新）"""
        w = self.preview_window
        if w is None:
            return
        try:
            w.apply_settings(settings)
        except Exception:
            pass

    def on_request_refresh_params(self):
        """重新从最新打开的预览窗口枚举参数和部件并重建UI"""
        latest = self.preview_window
        if latest is None:
            return
        try:
            canvas = latest.live2d_canvas
            meta = canvas.getParameterMetaList() if canvas else []
            self.settings_panel.rebuild_advanced_params(meta)
            parts = canvas.getPartIds() if canvas else []
            if hasattr(self.settings_panel, 'rebuild_parts_opacity'):
                self.settings_panel.rebuild_parts_opacity(parts)
        except Exception:
            pass
