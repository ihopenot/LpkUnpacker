import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QSlider, QCheckBox, QColorDialog,
                             QGroupBox, QSpinBox, QApplication, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QColor, QPalette, QMouseEvent, QPaintEvent, QFont
from qfluentwidgets import (PushButton, Slider, CheckBox, SubtitleLabel, BodyLabel, SpinBox)
try:
    from qfluentwidgets import Card
except ImportError:
    # 如果无法导入Card，使用标准PyQt组件作为替代
    class Card(QFrame):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setFrameStyle(QFrame.Box)
            self.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 5px;
                }
            """)
from GUI.Live2DWidget import Live2DWidget


class Live2DPreviewWindow(QWidget):
    """无边框的Live2D模型预览窗口"""

    closed = pyqtSignal()  # 窗口关闭信号

    def __init__(self, model_path=None, parent=None):
        super().__init__(parent)
        self.model_path = model_path
        self.live2d_widget = None
        self.dragging = False
        self.drag_position = QPoint()

        # 设置无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            Live2DPreviewWindow {
                background: transparent;
            }
        """)

        # 设置窗口大小和位置
        self.resize(400, 600)
        self.move_to_screen_center()

        # 初始化UI
        self.setup_ui()

        # 加载模型
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)

        # 设置关闭定时器（可选，用于自动关闭）
        self.auto_close_timer = QTimer()
        self.auto_close_timer.setSingleShot(True)

    def setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 创建Live2D显示区域
        self.live2d_widget = Live2DWidget(self)
        self.live2d_widget.setMinimumSize(300, 400)

        # 设置Live2D widget样式
        self.live2d_widget.setStyleSheet("""
            Live2DWidget {
                background: transparent;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 10px;
            }
            Live2DWidget:hover {
                border: 2px solid rgba(255, 255, 255, 0.5);
            }
        """)

        layout.addWidget(self.live2d_widget)

        # 创建控制面板（可隐藏）
        self.control_panel = self.create_control_panel()
        self.control_panel.setVisible(False)  # 默认隐藏
        layout.addWidget(self.control_panel)

    def create_control_panel(self):
        """创建控制面板"""
        panel = Card(self)
        panel.setFixedHeight(150)
        panel.setStyleSheet("""
            Card {
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

        # 置顶切换按钮
        self.stay_on_top_btn = PushButton("Stay On Top: ON", panel)
        self.stay_on_top_btn.clicked.connect(self.toggle_stay_on_top)
        button_layout.addWidget(self.stay_on_top_btn)

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

    def load_model(self, model_path):
        """加载Live2D模型"""
        if self.live2d_widget and os.path.exists(model_path):
            success = self.live2d_widget.load(model_path)
            if success:
                self.model_path = model_path
                self.setWindowTitle(f"Live2D Preview - {os.path.basename(model_path)}")
                # 设置默认鼠标交互
                self.live2d_widget.set_mouse_settings(
                    tracking_enabled=True,
                    drag_enabled=True,
                    sensitivity=1.0
                )
            return success
        return False

    def apply_settings(self, settings):
        """应用设置到预览窗口和Live2D模型"""
        if not settings:
            return

        # 应用窗口设置
        if 'window_size' in settings:
            self.resize(*settings['window_size'])

        if 'opacity' in settings:
            self.setWindowOpacity(settings['opacity'])
            if self.live2d_widget:
                self.live2d_widget.setCanvasOpacity(settings['opacity'])

        if 'stay_on_top' in settings:
            flags = self.windowFlags()
            if settings['stay_on_top']:
                flags |= Qt.WindowStaysOnTopHint
            else:
                flags &= ~Qt.WindowStaysOnTopHint
            self.setWindowFlags(flags)

        # 应用鼠标交互设置
        if self.live2d_widget and all(key in settings for key in ['mouse_tracking', 'mouse_drag', 'sensitivity']):
            self.live2d_widget.set_mouse_settings(
                tracking_enabled=settings['mouse_tracking'],
                drag_enabled=settings['mouse_drag'],
                sensitivity=settings['sensitivity'] / 5.0  # 将1-10范围转换为0.2-2.0
            )

    def toggle_control_panel(self):
        """切换控制面板显示/隐藏"""
        if self.control_panel.isVisible():
            self.control_panel.setVisible(False)
            self.toggle_controls_btn.setText("Show Controls")
            # 调整窗口大小
            self.resize(self.width(), self.live2d_widget.height() + 20)
        else:
            self.control_panel.setVisible(True)
            self.toggle_controls_btn.setText("Hide Controls")
            # 调整窗口大小
            self.resize(self.width(), self.live2d_widget.height() + self.control_panel.height() + 20)

    def toggle_stay_on_top(self):
        """切换窗口置顶状态"""
        flags = self.windowFlags()
        if flags & Qt.WindowStaysOnTopHint:
            # 取消置顶
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
            self.stay_on_top_btn.setText("Stay On Top: OFF")
        else:
            # 设置置顶
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
            self.stay_on_top_btn.setText("Stay On Top: ON")
        self.show()  # 重新显示窗口

    def on_opacity_changed(self, value):
        """透明度变化处理"""
        opacity = value / 100.0
        self.setWindowOpacity(opacity)
        if self.live2d_widget:
            self.live2d_widget.setCanvasOpacity(opacity)

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
            # 将鼠标事件传递给Live2D widget
            if self.live2d_widget:
                relative_pos = self.live2d_widget.mapFromParent(event.pos())
                if self.live2d_widget.rect().contains(relative_pos):
                    new_event = QMouseEvent(event.type(), relative_pos, event.button(),
                                          event.buttons(), event.modifiers())
                    self.live2d_widget.mouseMoveEvent(new_event)

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
        elif event.key() == Qt.Key_T:
            self.toggle_stay_on_top()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.live2d_widget:
            self.live2d_widget.release()
        self.closed.emit()
        super().closeEvent(event)

    def contextMenuEvent(self, event):
        """右键菜单事件"""
        # 可以在这里添加右键菜单功能
        pass