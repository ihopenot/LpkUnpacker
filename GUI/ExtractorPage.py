import os
import re
import logging
from PyQt5.QtCore import pyqtSignal, QThread, QUrl, Qt
from PyQt5.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QFileDialog, QApplication, QSizePolicy
from PyQt5.QtGui import QDesktopServices, QFont, QDragEnterEvent, QDropEvent
from qfluentwidgets import (
    PushButton, LineEdit, ComboBox, ProgressBar, TextEdit, SubtitleLabel,
    FluentIcon, InfoBar, InfoBarPosition, MessageBox
)

from Core.settings_manager import SettingsManager

# Logger class for GUI output
class QTextEditLogger(logging.Handler):
    def __init__(self, textEdit):
        super().__init__()
        self.textEdit = textEdit
        self.textEdit.setReadOnly(True)
        self.formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        
    def emit(self, record):
        msg = self.formatter.format(record)
        self.textEdit.append(msg)
        # Auto-scroll to the bottom
        scrollbar = self.textEdit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

# Thread for extraction
class ExtractorThread(QThread):
    progressUpdated = pyqtSignal(int)
    extractionFinished = pyqtSignal(str)
    extractionError = pyqtSignal(str)
    
    def __init__(self, lpk_path, config_path, output_dir):
        super().__init__()
        self.lpk_path = lpk_path
        self.config_path = config_path
        self.output_dir = output_dir
        
    def run(self):
        try:
            # Import inside the method to prevent early loading
            from Core.lpk_loader import LpkLoader
            loader = LpkLoader(self.lpk_path, self.config_path)
            loader.extract(self.output_dir)
            self.extractionFinished.emit(self.output_dir)
        except Exception as e:
            self.extractionError.emit(str(e))

class ExtractorPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Set object name - required for FluentWindow navigation
        self.setObjectName('extractorPage')
        
        # Initialize settings manager
        self.settings_manager = SettingsManager()
        
        # Enable drop
        self.setAcceptDrops(True)
        
        # Default output directory
        self.default_output_dir = self.settings_manager.get("last_output_path", os.path.join(os.getcwd(), "output"))
        
        self.setupUI()
        self.configure_logging()
        self.load_saved_paths()
        
        # 响应窗口大小变化
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def setupUI(self):
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(10)
        
        # Add title
        self.title_label = SubtitleLabel("LPK File Extractor", self)
        self.main_layout.addWidget(self.title_label)
        
        # LPK file selection
        self.lpk_layout = QHBoxLayout()
        self.lpk_label = SubtitleLabel("LPK File:", self)
        self.lpk_edit = LineEdit(self)
        self.lpk_edit.setPlaceholderText("Select LPK file or drag & drop file here...")
        self.lpk_button = PushButton("Browse", self)
        self.lpk_button.setIcon(FluentIcon.FOLDER)
        self.lpk_button.clicked.connect(self.browse_lpk)
        self.lpk_layout.addWidget(self.lpk_label)
        self.lpk_layout.addWidget(self.lpk_edit, 1)
        self.lpk_layout.addWidget(self.lpk_button)
        self.main_layout.addLayout(self.lpk_layout)
        
        # Config file selection (optional)
        self.config_layout = QHBoxLayout()
        self.config_label = SubtitleLabel("Config File:", self)
        self.config_edit = LineEdit(self)
        self.config_edit.setPlaceholderText("Select config.json (required for Steam workshop files)")
        self.config_button = PushButton("Browse", self)
        self.config_button.setIcon(FluentIcon.FOLDER)
        self.config_button.clicked.connect(self.browse_config)
        self.config_layout.addWidget(self.config_label)
        self.config_layout.addWidget(self.config_edit, 1)
        self.config_layout.addWidget(self.config_button)
        self.main_layout.addLayout(self.config_layout)
        
        # Output directory selection
        self.output_layout = QHBoxLayout()
        self.output_label = SubtitleLabel("Output Directory:", self)
        self.output_edit = LineEdit(self)
        self.output_edit.setPlaceholderText("Select output directory...")
        # Set default output directory
        self.output_edit.setText(self.default_output_dir)
        self.output_button = PushButton("Browse", self)
        self.output_button.setIcon(FluentIcon.FOLDER)
        self.output_button.clicked.connect(self.browse_output)
        self.output_layout.addWidget(self.output_label)
        self.output_layout.addWidget(self.output_edit, 1)
        self.output_layout.addWidget(self.output_button)
        self.main_layout.addLayout(self.output_layout)
        
        # Progress bar
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.main_layout.addWidget(self.progress_bar)
        
        # Extract button
        self.extract_button = PushButton("Extract", self)
        self.extract_button.setIcon(FluentIcon.PLAY)
        self.extract_button.clicked.connect(self.start_extraction)
        self.main_layout.addWidget(self.extract_button)
        
        # Open output folder button
        self.open_folder_button = PushButton("Open Output Folder", self)
        self.open_folder_button.setIcon(FluentIcon.FOLDER)
        self.open_folder_button.clicked.connect(self.open_output_folder)
        self.open_folder_button.setEnabled(False)
        self.main_layout.addWidget(self.open_folder_button)
        
        # Log output
        self.log_label = SubtitleLabel("Log:", self)
        self.main_layout.addWidget(self.log_label)
        
        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        self.main_layout.addWidget(self.log_text)
        
        # 确保所有按钮有合理的最小尺寸
        for button in self.findChildren(PushButton):
            button.setMinimumSize(100, 30)
            
        # 设置LineEdit的最小高度
        for line_edit in self.findChildren(LineEdit):
            line_edit.setMinimumHeight(30)
            
        # 设置TextEdit的响应式尺寸
        self.log_text.setMinimumHeight(200)
        self.log_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    # Drag & Drop support
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            # Accept only files with .lpk or .json extensions
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                ext = os.path.splitext(path)[1].lower()
                if ext == '.lpk' or ext == '.json':
                    event.acceptProposedAction()
                    return
                    
    def dropEvent(self, event: QDropEvent):
        # Process the dropped files
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            ext = os.path.splitext(path)[1].lower()
            
            # Handle LPK file
            if ext == '.lpk':
                self.lpk_edit.setText(path)
                # Try to find config.json in same directory
                dir_path = os.path.dirname(path)
                potential_config = os.path.join(dir_path, "config.json")
                if os.path.exists(potential_config):
                    self.config_edit.setText(potential_config)
                    
            # Handle JSON config file
            elif ext == '.json' and os.path.basename(path).lower() == 'config.json':
                self.config_edit.setText(path)
                
        event.acceptProposedAction()
        
    def configure_logging(self):
        # Setup logging to capture to text widget
        self.log_handler = QTextEditLogger(self.log_text)
        self.log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(self.log_handler)
        
    def browse_lpk(self):
        # Get last used directory
        last_dir = os.path.dirname(self.settings_manager.get("last_lpk_path", ""))
        if not last_dir or not os.path.exists(last_dir):
            last_dir = os.getcwd()
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select LPK File", last_dir, "LPK Files (*.lpk)"
        )
        if file_path:
            # Use absolute path
            file_path = os.path.abspath(file_path)
            self.lpk_edit.setText(file_path)
            self.settings_manager.set("last_lpk_path", file_path)
            self.settings_manager.add_recent_file(file_path, "lpk")
            # Try to auto-locate config.json in the same directory
            dir_name = os.path.dirname(file_path)
            potential_config = os.path.join(dir_name, "config.json")
            if os.path.exists(potential_config):
                self.config_edit.setText(potential_config)
                
    def browse_config(self):
        """Browse for config file"""
        # Get last used directory
        last_dir = os.path.dirname(self.settings_manager.get("last_config_path", ""))
        if not last_dir or not os.path.exists(last_dir):
            last_dir = os.getcwd()
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择配置文件", 
            last_dir,
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.config_edit.setText(file_path)
            self.settings_manager.set("last_config_path", file_path)
            self.settings_manager.add_recent_file(file_path, "config")
            
    def browse_output(self):
        """Browse for output directory"""
        # Get last used directory
        last_dir = self.settings_manager.get("last_output_path", self.default_output_dir)
        if not os.path.exists(last_dir):
            last_dir = os.getcwd()
            
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            "选择输出目录", 
            last_dir
        )
        if dir_path:
            self.output_edit.setText(dir_path)
            self.settings_manager.set("last_output_path", dir_path)
            
    def normalize_path(self, path):
        """
        Normalize path to ensure consistent format and handle relative/absolute paths correctly
        """
        # Convert all backslashes to forward slashes
        path = path.replace('\\', '/')
        
        # Handle absolute paths - for Windows that starts with drive letter (e.g., D:/)
        if re.match(r'^[a-zA-Z]:/.*', path):
            # Already absolute path, just ensure proper format
            return path
        
        # Handle paths starting with leading / (Unix absolute paths)
        if path.startswith('/'):
            return path
            
        # For relative paths, ensure no duplication of directory structure
        # Remove any leading ./ or D:/ etc.
        path = re.sub(r'^\.?[/\\]', '', path)
        path = re.sub(r'^[a-zA-Z]:[/\\]', '', path)
        
        return path
        
    def start_extraction(self):
        # Save current paths before extraction
        self.save_current_paths()
        
        # Validate inputs
        lpk_path = self.lpk_edit.text()
        config_path = self.config_edit.text()
        output_dir = self.output_edit.text()
        
        # Convert to absolute paths
        if lpk_path:
            lpk_path = os.path.abspath(lpk_path)
        if config_path:
            config_path = os.path.abspath(config_path)
        if output_dir:
            output_dir = os.path.abspath(output_dir)
        else:
            # Use default output directory
            output_dir = os.path.abspath(self.default_output_dir)
            self.output_edit.setText(output_dir)
        
        if not lpk_path or not os.path.exists(lpk_path):
            InfoBar.error(
                title="Error",
                content="Please select a valid LPK file.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return
            
        if not output_dir:
            # If output directory is empty, use default
            output_dir = self.default_output_dir
            self.output_edit.setText(output_dir)
            
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except OSError as e:
                InfoBar.error(
                    title="Error",
                    content=f"Failed to create output directory: {str(e)}",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
                return
        
        # Determine if we're using default output or custom directory
        is_default_output = os.path.normpath(output_dir) == os.path.normpath(self.default_output_dir)
                
        # Set verbosity level - now fixed to INFO
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Disable controls during extraction
        self.extract_button.setEnabled(False)
        
        # Fix: Use setValue(1) and disable the range to show indeterminate progress
        # instead of using setIndeterminate(True) which doesn't exist
        self.progress_bar.setRange(0, 0)  # No range = indeterminate
        
        # Start extraction in a separate thread
        self.extractor_thread = ExtractorThread(lpk_path, config_path, output_dir)
        self.extractor_thread.extractionFinished.connect(self.extraction_finished)
        self.extractor_thread.extractionError.connect(self.extraction_error)
        self.extractor_thread.start()
        
        # Log start of extraction
        logging.info(f"Starting extraction of {lpk_path} to {output_dir}")
        
    def extraction_finished(self, output_dir):
        # Re-enable controls
        self.extract_button.setEnabled(True)
        # Fix: Restore normal range and set to 100%
        self.progress_bar.setRange(0, 100) 
        self.progress_bar.setValue(100)
        self.open_folder_button.setEnabled(True)
        
        # Show success message
        InfoBar.success(
            title="Success",
            content=f"LPK file extracted successfully to {output_dir}",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=5000
        )
        
        logging.info(f"Extraction completed successfully. Files saved to {output_dir}")
        
    def extraction_error(self, error_message):
        # Re-enable controls
        self.extract_button.setEnabled(True)
        # Fix: Restore normal range and set to 0%
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # Show error message
        MessageBox(
            "Extraction Error",
            error_message,
            self
        ).exec_()
        
        logging.error(f"Extraction failed: {error_message}")
        
    def open_output_folder(self):
        output_dir = self.output_edit.text()
        if os.path.exists(output_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))
        else:
            InfoBar.warning(
                title="Warning",
                content="Output directory does not exist.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            
    def updateUIScale(self, window_width, window_height):
        """根据窗口大小调整UI元素"""
        # 计算比例因子
        scale_factor = max(1.0, window_width / 1000.0)
        
        # 调整按钮大小
        button_height = int(30 * scale_factor)
        for button in self.findChildren(PushButton):
            button.setMinimumHeight(button_height)
            
        # 调整输入框高度
        for line_edit in self.findChildren(LineEdit):
            line_edit.setMinimumHeight(button_height)
            
        # 调整字体大小
        font = QApplication.instance().font()
        for label in self.findChildren(SubtitleLabel):
            label_font = label.font()
            label_font.setPointSize(font.pointSize() + 2)  # 标题字体比正常字体大2点
            label.setFont(label_font)
            
        # 日志窗口自适应
        self.log_text.setMinimumHeight(int(200 * scale_factor))
    
    def load_saved_paths(self):
        """Load previously saved paths"""
        # Load last used paths
        last_lpk = self.settings_manager.get("last_lpk_path", "")
        last_config = self.settings_manager.get("last_config_path", "")
        last_output = self.settings_manager.get("last_output_path", self.default_output_dir)
        
        if last_lpk and os.path.exists(last_lpk):
            self.lpk_edit.setText(last_lpk)
            
        if last_config and os.path.exists(last_config):
            self.config_edit.setText(last_config)
            
        if last_output:
            self.output_edit.setText(last_output)
    
    def save_current_paths(self):
        """Save current paths to settings"""
        lpk_path = self.lpk_edit.text().strip()
        config_path = self.config_edit.text().strip()
        output_path = self.output_edit.text().strip()
        
        if lpk_path:
            self.settings_manager.set("last_lpk_path", lpk_path)
            self.settings_manager.add_recent_file(lpk_path, "lpk")
            
        if config_path:
            self.settings_manager.set("last_config_path", config_path)
            self.settings_manager.add_recent_file(config_path, "config")
            
        if output_path:
            self.settings_manager.set("last_output_path", output_path)
        
        # 进度条高度
        self.progress_bar.setMinimumHeight(int(20 * scale_factor))
