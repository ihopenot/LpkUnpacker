import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QApplication)
from PyQt5.QtCore import pyqtSignal, QPoint, Qt, QEvent
from qfluentwidgets import (PushButton, SubtitleLabel, BodyLabel)
from qfluentwidgets import CardWidget
from qfluentwidgets import ComboBox
from qfluentwidgets import InfoBar, InfoBarPosition

from GUI.Live2DCanvas import Live2DCanvas


class Live2DPreviewWindow(QWidget):
    """无边框的Live2D模型预览窗口"""

    closed = pyqtSignal()  # 窗口关闭信号

    def __init__(self, model_path=None):
        super().__init__()
        self.model_path = model_path
        self.live2d_canvas = None
        self.control_panel = None
        self.dragging = False
        self.drag_position = QPoint()
        self._selected_motion = None  # tuple(group, index)
        self._motion_items = []  # [(group, index, display)]

        # 设置无边框窗口
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.Tool, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 设置窗口大小和位置
        self.resize(400, 300)
        self.move_to_screen_center()

        # 初始化UI
        self.setup_ui()

    # 新增：统一的错误提示
    def _show_error_infobar(self, content: str, title: str = "Error"):
        try:
            # 优先将 InfoBar 挂到主窗口/其他顶层窗口上，避免当前预览窗口关闭后看不到提示
            parent = QApplication.activeWindow()
            if parent is None or parent is self:
                for w in QApplication.topLevelWidgets():
                    if w is not self and w.isVisible():
                        parent = w
                        break
            InfoBar.error(
                title=title,
                content=content,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=parent if parent is not None else self
            )
        except Exception:
            print(f"[Error] {title}: {content}")

    def setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 统一确定模型路径
        if not self.model_path or not os.path.exists(self.model_path):
            self._show_error_infobar(f"Model file does not exist: {self.model_path}")
            self.close()
            return

        # 创建Live2D显示区域并捕获异常
        try:
            self.live2d_canvas = Live2DCanvas(self.model_path)
        except Exception as e:
            # 显示错误并关闭窗口
            self._show_error_infobar(f"Unexpected error occurred while loading, {type(e).__name__}: {e}.")
            self.close()
            return
        # 设置Live2D widget样式
        self.live2d_canvas.setStyleSheet("""
            Live2DCanvas {
                background: transparent;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 10px;
            }
            Live2DCanvas:hover {
                border: 2px solid rgba(255, 255, 255, 0.5);
            }
        """)

        # 监听canvas右键
        self.live2d_canvas.installEventFilter(self)
        layout.addWidget(self.live2d_canvas)
        # 创建控制面板（可隐藏）
        self.control_panel = self.create_control_panel()
        self.control_panel.setVisible(False)  # 默认隐藏
        layout.addWidget(self.control_panel)

    def create_control_panel(self):
        """创建控制面板"""
        panel = CardWidget(self)
        panel.setFixedHeight(180)
        panel.setStyleSheet("""
            CardWidget {
                background: rgba(30, 30, 30, 0.9);
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题
        title = SubtitleLabel("Live2D Controls", panel)
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        # 动作选择
        row = QHBoxLayout()
        lbl = BodyLabel("Right-Click Action", panel)
        lbl.setStyleSheet("color: white;")
        row.addWidget(lbl)
        self.motion_combo = ComboBox(panel)
        self.motion_combo.setMinimumWidth(220)
        # 填充动作列表
        self._populate_motion_combo()
        # 保存选择
        self.motion_combo.currentIndexChanged.connect(self._on_motion_changed)
        row.addWidget(self.motion_combo, 1)
        layout.addLayout(row)

        # 控制按钮行
        button_layout = QHBoxLayout()

        # 切换控制面板按钮
        self.toggle_controls_btn = PushButton("Hide Controls", panel)
        self.toggle_controls_btn.clicked.connect(self.toggle_control_panel)
        button_layout.addWidget(self.toggle_controls_btn)

        # 关闭按钮
        close_btn = PushButton("Close", panel)
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        return panel

    def _populate_motion_combo(self):
        """读取model*.json中的动作并填充到下拉框"""
        import json
        self.motion_combo.clear()
        self._motion_items = []
        self._selected_motion = None
        if not self.model_path or not os.path.exists(self.model_path):
            return
        try:
            with open(self.model_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            refs = (data or {}).get('FileReferences') or {}
            groups = refs.get('Motions') or {}
            for g, items in groups.items():
                if not isinstance(items, list):
                    continue
                for idx, it in enumerate(items):
                    rel = (it or {}).get('File') or ''
                    display = f"{g}[{idx}] - {os.path.basename(rel) if rel else ''}"
                    self._motion_items.append((g, idx, display))
        except Exception:
            self._motion_items = []
        if not self._motion_items:
            self.motion_combo.addItem("(No motions available)")
            self.motion_combo.setEnabled(False)
            return
        self.motion_combo.setEnabled(True)
        for (_, _, disp) in self._motion_items:
            self.motion_combo.addItem(disp)
        # 默认选中第一个
        self.motion_combo.setCurrentIndex(0)
        self._on_motion_changed(0)

    def _on_motion_changed(self, i: int):
        if 0 <= i < len(self._motion_items):
            g, idx, _ = self._motion_items[i]
            self._selected_motion = (str(g), int(idx))
        else:
            self._selected_motion = None

    def eventFilter(self, obj, event):
        # 在canvas上右键 -> 播放选中动作
        if obj is self.live2d_canvas and event.type() == QEvent.MouseButtonPress:
            try:
                if event.button() == Qt.RightButton and self._selected_motion:
                    group, index = self._selected_motion
                    # 调用画布播放
                    try:
                        self.live2d_canvas.playMotion(group, index)
                    except Exception:
                        pass
                    return True
            except Exception:
                pass
        return super().eventFilter(obj, event)

    def move_to_screen_center(self):
        """将窗口移动到屏幕中央"""
        screen = QApplication.desktop().screenGeometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)

    def apply_settings(self, settings):
        """应用设置到预览窗口和Live2D模型"""
        if not settings:
            return

        # 应用窗口设置
        if 'window_size' in settings:
            w, h = settings['window_size']
            # 当控制面板可见时，窗口总高度 = 目标画布高度 + 控制面板高度
            extra_h = 0
            try:
                if self.control_panel is not None and self.control_panel.isVisible():
                    extra_h = int(self.control_panel.height())
            except Exception:
                extra_h = 0
            total_h = int(h) + extra_h
            try:
                self.resize(int(w), int(total_h))
            except Exception:
                self._show_error_infobar("Failed to resize preview window.")

        # 画布透明度（模型不透明度）
        if 'opacity' in settings and self.live2d_canvas:
            self.live2d_canvas.setCanvasOpacity(settings['opacity'])

        # 模型旋转
        if 'model_rotation' in settings and self.live2d_canvas:
            self.live2d_canvas.setRotationAngle(settings['model_rotation'])

        # 背景透明/颜色
        if self.live2d_canvas and ('transparent_bg' in settings or 'bg_color' in settings):
            transparent = bool(settings.get('transparent_bg', True))
            qcolor = settings.get('bg_color')
            self.live2d_canvas.setBackground(transparent, qcolor)

        # 鼠标跟踪
        if 'mouse_tracking' in settings and self.live2d_canvas:
            self.live2d_canvas.setMouseTracking(bool(settings['mouse_tracking']))

        # 自动眨眼/呼吸
        if 'auto_blink' in settings and self.live2d_canvas:
            self.live2d_canvas.setAutoBlinkEnable(bool(settings['auto_blink']))
        if 'auto_breath' in settings and self.live2d_canvas:
            self.live2d_canvas.setAutoBreathEnable(bool(settings['auto_breath']))

        # 高级参数
        if self.live2d_canvas and ('advanced_enabled' in settings or 'advanced_params' in settings):
            enabled = bool(settings.get('advanced_enabled', False))
            params = settings.get('advanced_params', {}) or {}
            self.live2d_canvas.setAdvancedParams(enabled, params)

    def toggle_control_panel(self):
        """切换控制面板显示/隐藏"""
        if self.control_panel.isVisible():
            self.control_panel.setVisible(False)
            self.toggle_controls_btn.setText("Show Controls")
            # 调整窗口大小
            self.resize(self.width(), self.height() - self.control_panel.height())
        else:
            self.control_panel.setVisible(True)
            self.toggle_controls_btn.setText("Hide Controls")
            # 调整窗口大小
            self.resize(self.width(), self.height() + self.control_panel.height())

    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于拖拽窗口"""
        if event.button() == Qt.LeftButton:
            # 检查是否点击在控制面板区域
            if self.control_panel.isVisible():
                control_rect = self.control_panel.geometry()
                if control_rect.contains(event.pos()):
                    return  # 在控制面板区域，不启动拖拽

            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖拽窗口"""
        if event.buttons() == Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
        else:
            pass

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def mouseDoubleClickEvent(self, event):
        """双击事件 - 切换控制面板"""
        if event.button() == Qt.LeftButton:
            self.toggle_control_panel()

    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Space:
            self.toggle_control_panel()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.live2d_canvas:
            self.live2d_canvas.release()
        self.closed.emit()
        super().closeEvent(event)

    def contextMenuEvent(self, event):
        """右键菜单事件"""
        pass
