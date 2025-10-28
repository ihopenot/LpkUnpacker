import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QApplication)
from PyQt5.QtCore import pyqtSignal, QPoint, Qt
from qfluentwidgets import (PushButton, Slider, SubtitleLabel, BodyLabel)
from qfluentwidgets import CardWidget

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

        # 设置无边框窗口
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.Tool, True)
        # Use explicit enum for linter friendliness
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 设置窗口大小和位置
        self.resize(400, 300)
        self.move_to_screen_center()

        # 初始化UI
        self.setup_ui()


    def setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if self.model_path and os.path.exists(self.model_path):
            # 创建Live2D显示区域
            self.live2d_canvas = Live2DCanvas(self.model_path)
        else:
            self.live2d_canvas = Live2DCanvas("./runtime/hiyori_free_t08.model3.json")

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

        layout.addWidget(self.live2d_canvas)

        # 创建控制面板（可隐藏）
        self.control_panel = self.create_control_panel()
        self.control_panel.setVisible(False)  # 默认隐藏
        layout.addWidget(self.control_panel)

    def create_control_panel(self):
        """创建控制面板"""
        panel = CardWidget(self)
        panel.setFixedHeight(150)
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

        # 透明度控制
        opacity_layout = QHBoxLayout()
        opacity_label = BodyLabel("Opacity:", panel)
        opacity_label.setStyleSheet("color: white;")
        self.opacity_slider = Slider(Qt.Horizontal, panel)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)

        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self.opacity_slider)
        layout.addLayout(opacity_layout)

        return panel

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
            try:
                self.resize(int(w), int(h))
            except Exception:
                self.resize(w, h)

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

    def on_opacity_changed(self, value):
        """透明度变化处理"""
        opacity = value / 100.0
        if self.live2d_canvas:
            self.live2d_canvas.setCanvasOpacity(opacity)

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
        # 可以在这里添加右键菜单功能
        pass

if __name__ == "__main__":
    from PyQt5.QtCore import Qt, QCoreApplication

    # Use ApplicationAttribute enum for clarity
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    window = Live2DPreviewWindow()
    window.show()

    window2 = Live2DPreviewWindow()
    window2.show()
    sys.exit(app.exec_())