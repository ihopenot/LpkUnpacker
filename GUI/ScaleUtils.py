from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QFont
from qfluentwidgets import SubtitleLabel, PushButton, LineEdit

class UIScaler:
    @staticmethod
    def scale_widgets(parent_widget, window_width):
        """为给定的父widget内的所有控件适配缩放"""
        # 计算比例因子
        scale_factor = max(1.0, window_width / 1000.0)
        
        # 调整按钮大小
        button_height = int(30 * scale_factor)
        for button in parent_widget.findChildren(PushButton):
            button.setMinimumHeight(button_height)
            
        # 调整输入框高度
        for line_edit in parent_widget.findChildren(LineEdit):
            line_edit.setMinimumHeight(button_height)
            
        # 调整字体大小
        font = QApplication.instance().font()
        for label in parent_widget.findChildren(SubtitleLabel):
            label_font = label.font()
            label_font.setPointSize(font.pointSize() + 2)  # 标题字体比正常字体大2点
            label.setFont(label_font)
        
        return scale_factor
