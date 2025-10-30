from PyQt5.QtWidgets import QApplication, QFrame, QHBoxLayout, QMessageBox, QSizePolicy
from PyQt5.QtCore import Qt, QEvent, QSize
from PyQt5.QtGui import QIcon, QFont, QResizeEvent
from qfluentwidgets import NavigationItemPosition, FluentWindow, setTheme, Theme, setFont
from qfluentwidgets import FluentIcon as FIF

# Import pages - using try/except to handle potential import errors
try:
    from GUI.ExtractorPage import ExtractorPage
except Exception as e:
    import traceback
    print(f"Error importing ExtractorPage: {e}")
    traceback.print_exc()
    # Create a dummy page to prevent app crash
    class ExtractorPage(QFrame):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName('extractorPage')
            QHBoxLayout(self).addWidget(QFrame(self))

try:
    from GUI.PreviewPage import PreviewPage
except Exception as e:
    import traceback
    print(f"Error importing PreviewPage: {e}")
    traceback.print_exc()
    # Create a dummy page
    class PreviewPage(QFrame):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName('previewPage')
            QHBoxLayout(self).addWidget(QFrame(self))

try:
    from GUI.EncryptionPage import EncryptionPage
except Exception as e:
    import traceback
    print(f"Error importing EncryptionPage: {e}")
    traceback.print_exc()
    # Create a dummy page
    class EncryptionPage(QFrame):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName('encryptionPage')
            QHBoxLayout(self).addWidget(QFrame(self))

try:
    from GUI.SteamWorkshopPage import SteamWorkshopPage
except Exception as e:
    import traceback
    print(f"Error importing SteamWorkshopPage: {e}")
    traceback.print_exc()
    # Create a dummy page
    class SteamWorkshopPage(QFrame):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName('steamWorkshopPage')
            QHBoxLayout(self).addWidget(QFrame(self))


class MainWindow(FluentWindow):
    """ Main Window with Navigation """
    
    def __init__(self):
        super().__init__()
        
        # Create sub-interfaces
        try:
            self.extractorPage = ExtractorPage(self)
        except Exception as e:
            print(f"Error creating ExtractorPage: {e}")
            self.extractorPage = QFrame(self)
            self.extractorPage.setObjectName('extractorPage')
            
        try:
            self.previewPage = PreviewPage(self)
        except Exception as e:
            print(f"Error creating PreviewPage: {e}")
            self.previewPage = QFrame(self)
            self.previewPage.setObjectName('previewPage')
            
        try:
            self.encryptionPage = EncryptionPage(self)
        except Exception as e:
            print(f"Error creating EncryptionPage: {e}")
            self.encryptionPage = QFrame(self)
            self.encryptionPage.setObjectName('encryptionPage')
            
        try:
            self.steamWorkshopPage = SteamWorkshopPage(self)
        except Exception as e:
            print(f"Error creating SteamWorkshopPage: {e}")
            self.steamWorkshopPage = QFrame(self)
            self.steamWorkshopPage.setObjectName('steamWorkshopPage')

        self.initWindow()
        self.initNavigation()
        
        # Set theme
        setTheme(Theme.AUTO)
        
        # 为整个应用设置字体
        self.updateFontSize()
        
        # 安装事件过滤器以处理缩放
        self.installEventFilter(self)
        
    def initWindow(self):
        self.resize(1000, 700)  # 稍微增大初始窗口尺寸
        self.setWindowTitle('LPK Unpacker GUI')
        
    def initNavigation(self):
        # Add sub-interfaces to navigation
        try:
            self.addSubInterface(self.extractorPage, FIF.ZIP_FOLDER, 'LPK Extractor')
        except Exception as e:
            print(f"Error adding ExtractorPage to navigation: {e}")
            
        try:
            self.addSubInterface(self.steamWorkshopPage, FIF.GAME, 'Steam Workshop')
        except Exception as e:
            print(f"Error adding SteamWorkshopPage to navigation: {e}")
            
        try:
            self.addSubInterface(self.previewPage, FIF.MOVIE, 'Live2D Preview')
        except Exception as e:
            print(f"Error adding PreviewPage to navigation: {e}")

        self.navigationInterface.addSeparator()
            
        try:
            self.addSubInterface(self.encryptionPage, FIF.DOWNLOAD, 'Encryption Package Extractor',
                              NavigationItemPosition.SCROLL)
        except Exception as e:
            print(f"Error adding EncryptionPage to navigation: {e}")
            
    def eventFilter(self, obj, event):
        # 监听窗口大小变化事件，调整字体和控件大小
        if obj is self and event.type() == QEvent.Resize:
            self.updateFontSize()
        
        return super().eventFilter(obj, event)
    
    def updateFontSize(self):
        """根据窗口大小更新字体"""
        # 基于窗口宽度计算字体大小因子
        width = self.width()
        # 根据窗口大小调整字体大小，从基础大小9开始
        base_size = 9
        if width > 1600:
            font_size = base_size + 3
        elif width > 1200:
            font_size = base_size + 2
        elif width > 800:
            font_size = base_size + 1
        else:
            font_size = base_size
            
        # 设置应用的字体
        app = QApplication.instance()
        font = app.font()
        font.setPointSize(font_size)
        app.setFont(font)
        
        # 确保子页面知道字体已更新
        for page in [self.extractorPage, self.previewPage, self.encryptionPage]:
            if hasattr(page, 'updateUIScale'):
                page.updateUIScale(self.width(), self.height())