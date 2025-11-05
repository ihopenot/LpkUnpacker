import sys
import os
from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

# 在创建QApplication之前设置QtWebEngine所需的属性
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
# 确保设置正确的属性来支持高DPI缩放
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

# 预先导入QtWebEngineWidgets以确保正确初始化
try:
    from PyQt5 import QtWebEngineWidgets
except ImportError:
    print("Warning: QtWebEngineWidgets not available. Web preview functionality will be disabled.")
    QtWebEngineWidgets = None

def run_application():
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 设置应用程序图标 - 这会影响任务栏图标
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Img/icon.ico")
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    
    # 设置全局字体缩放因子
    font = app.font()
    font.setPointSize(10)  # 设置一个基础字号大小
    app.setFont(font)
    
    try:
        # 导入主窗口类
        from GUI.MainWindow import MainWindow
        
        # 创建主窗口
        window = MainWindow()
        # 确保窗口也使用相同的图标
        window.setWindowIcon(app_icon)
        window.show()
        
        # 启动应用程序事件循环
        return app.exec_()
    except Exception as e:
        import traceback
        print(f"Error initializing application: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_application())