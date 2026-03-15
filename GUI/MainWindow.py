from PyQt5.QtWidgets import QApplication, QFrame, QHBoxLayout, QMessageBox, QSizePolicy
from PyQt5.QtCore import Qt, QEvent, QSize
from PyQt5.QtGui import QIcon, QFont, QResizeEvent
from qfluentwidgets import NavigationItemPosition, FluentWindow, setTheme, Theme, setFont
from qfluentwidgets import FluentIcon as FIF
from Core.settings_manager import SettingsManager
from Translations import get_i18n, tr, normalize_language_code
import os

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

# Conditionally import native preview page to avoid heavy dependencies in light builds
_DISABLE_NATIVE_PREVIEW = os.environ.get("LPK_DISABLE_NATIVE_PREVIEW", "0") == "1"
if not _DISABLE_NATIVE_PREVIEW:
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
else:
    # Define a minimal stub when native preview is disabled
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


# Try import SteamWorkshopPage with fallback
try:
    from GUI.SteamWorkshopPage import SteamWorkshopPage
except Exception as e:
    import traceback
    print(f"Error importing SteamWorkshopPage: {e}")
    traceback.print_exc()
    class SteamWorkshopPage(QFrame):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName('steamWorkshopPage')
            QHBoxLayout(self).addWidget(QFrame(self))

# Try import WebPreviewPage with fallback
try:
    from GUI.WebPreviewPage import WebPreviewPage
except Exception as e:
    import traceback
    print(f"Error importing WebPreviewPage: {e}")
    traceback.print_exc()
    class WebPreviewPage(QFrame):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName('webPreviewPage')
            QHBoxLayout(self).addWidget(QFrame(self))

# Try import SettingsPage with fallback
try:
    from GUI.SettingsPage import SettingsPage
except Exception as e:
    import traceback
    print(f"Error importing SettingsPage: {e}")
    traceback.print_exc()
    class SettingsPage(QFrame):
        languageChanged = None
        themeChanged = None
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName('settingsPage')
            QHBoxLayout(self).addWidget(QFrame(self))

class MainWindow(FluentWindow):
    """ Main Window with Navigation """
    
    def __init__(self):
        super().__init__()
        self.setMicaEffectEnabled(False)
        
        # Initialize settings manager
        self.settings_manager = SettingsManager()
        self.i18n = get_i18n()
        self.i18n.set_language(normalize_language_code(self.settings_manager.get("language", "en_US")))
        
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
        
        try:
            self.webPreviewPage = WebPreviewPage(self)
        except Exception as e:
            print(f"Error creating WebPreviewPage: {e}")
            self.webPreviewPage = QFrame(self)
            self.webPreviewPage.setObjectName('webPreviewPage')

        try:
            self.settingsPage = SettingsPage(self)
            language_changed = getattr(self.settingsPage, "languageChanged", None)
            theme_changed = getattr(self.settingsPage, "themeChanged", None)
            if language_changed is not None and hasattr(language_changed, "connect"):
                language_changed.connect(self.on_language_changed)
            if theme_changed is not None and hasattr(theme_changed, "connect"):
                theme_changed.connect(self.on_theme_changed)
        except Exception as e:
            print(f"Error creating SettingsPage: {e}")
            self.settingsPage = QFrame(self)
            self.settingsPage.setObjectName('settingsPage')

        self.initWindow()
        self.initNavigation()
        
        # Set theme from settings
        self.apply_theme()
        
        # 为整个应用设置字体
        self.updateFontSize()

        self.i18n.languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()
        
        # 安装事件过滤器以处理缩放
        self.installEventFilter(self)
        
    def initWindow(self):
        self.resize(1000, 700)  # 稍微增大初始窗口尺寸
        self.setWindowTitle(tr("main.window_title"))
        
    def initNavigation(self):
        # Add sub-interfaces to navigation
        try:
            self.addSubInterface(self.extractorPage, FIF.ZIP_FOLDER, tr("main.nav.extractor"))
        except Exception as e:
            print(f"Error adding ExtractorPage to navigation: {e}")

        try:
            self.addSubInterface(self.steamWorkshopPage, FIF.GAME, tr("main.nav.steam"))
        except Exception as e:
            print(f"Error adding SteamWorkshopPage to navigation: {e}")
            
        try:
            # Only add native preview tab when not disabled
            if not _DISABLE_NATIVE_PREVIEW:
                self.addSubInterface(self.previewPage, FIF.MOVIE, tr("main.nav.preview_native"))
        except Exception as e:
            print(f"Error adding PreviewPage to navigation: {e}")
            
        try:
            self.addSubInterface(self.webPreviewPage, FIF.GLOBE, tr("main.nav.preview_web"))
        except Exception as e:
            print(f"Error adding WebPreviewPage to navigation: {e}")

        self.navigationInterface.addSeparator()
            
        try:
            self.addSubInterface(self.encryptionPage, FIF.DOWNLOAD, tr("main.nav.encryption"),
                              NavigationItemPosition.SCROLL)
        except Exception as e:
            print(f"Error adding EncryptionPage to navigation: {e}")

        try:
            self.addSubInterface(
                self.settingsPage,
                FIF.SETTING,
                tr("main.nav.settings"),
                NavigationItemPosition.BOTTOM
            )
        except Exception as e:
            print(f"Error adding SettingsPage to navigation: {e}")
        
        # Steam Workshop already added to top navigation above
            
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
        
        pages = [
            self.extractorPage,
            self.previewPage,
            self.encryptionPage,
            getattr(self, 'steamWorkshopPage', None),
            getattr(self, 'webPreviewPage', None),
            getattr(self, 'settingsPage', None)
        ]
        for page in filter(None, pages):
            if hasattr(page, 'updateUIScale'):
                page.updateUIScale(self.width(), self.height())
    
    def apply_theme(self):
        """从设置中应用主题"""
        try:
            theme_setting = self.settings_manager.get('theme', 'light').lower()
            
            if theme_setting == 'light':
                setTheme(Theme.LIGHT)
            elif theme_setting == 'dark':
                setTheme(Theme.DARK)
            else:  # 'auto' or any other value
                setTheme(Theme.LIGHT)  # 默认使用浅色主题而不是AUTO
                
            # 强制设置窗口背景色为白色
            self.setStyleSheet("""
                QWidget {
                    background-color: white;
                    color: black;
                }
                QFrame {
                    background-color: white;
                }
            """)
                
            print(f"Applied theme: {theme_setting}")
        except Exception as e:
            print(f"Error applying theme: {e}")
            # Fallback to light theme
            setTheme(Theme.LIGHT)
            self.setStyleSheet("""
                QWidget {
                    background-color: white;
                    color: black;
                }
                QFrame {
                    background-color: white;
                }
            """)

    def retranslate_ui(self):
        self.setWindowTitle(tr("main.window_title"))

        for page in [
            self.extractorPage,
            self.previewPage,
            self.encryptionPage,
            getattr(self, "steamWorkshopPage", None),
            getattr(self, "webPreviewPage", None),
            getattr(self, "settingsPage", None),
        ]:
            if page is not None and hasattr(page, "retranslate_ui"):
                try:
                    page.retranslate_ui()
                except Exception as e:
                    print(f"Error re-translating {page.objectName()}: {e}")

    def on_language_changed(self, language: str):
        normalized = normalize_language_code(language)
        self.settings_manager.set("language", normalized)
        self.i18n.set_language(normalized)

    def on_theme_changed(self, theme: str):
        self.settings_manager.set("theme", str(theme).lower())
        self.apply_theme()
