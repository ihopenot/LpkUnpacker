import os
import logging
from typing import List, Dict
from PyQt5.QtCore import pyqtSignal, QThread, Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QFileDialog, QApplication, QSizePolicy, QHeaderView, QAbstractItemView,
    QLabel
)
from PyQt5.QtGui import QFont, QPixmap
from qfluentwidgets import (
    PushButton, LineEdit, ComboBox, ProgressBar, TextEdit, SubtitleLabel,
    FluentIcon, InfoBar, InfoBarPosition, MessageBox, TableWidget,
    CheckBox, ToolButton, CardWidget, BodyLabel, CaptionLabel
)

from Core.steam_integration import SteamIntegration
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

# Thread for Steam scanning
class SteamScanThread(QThread):
    scanFinished = pyqtSignal(list)
    scanError = pyqtSignal(str)
    
    def __init__(self, steam_path=None):
        super().__init__()
        self.steam_path = steam_path
        
    def run(self):
        try:
            steam_integration = SteamIntegration()
            if self.steam_path:
                workshop_items = steam_integration.scan_workshop_items(
                    steam_integration.get_workshop_path(self.steam_path)
                )
            else:
                workshop_items = steam_integration.scan_workshop_items()
            self.scanFinished.emit(workshop_items)
        except Exception as e:
            self.scanError.emit(str(e))

# Thread for batch extraction
class BatchExtractionThread(QThread):
    progressUpdated = pyqtSignal(int, str)
    extractionFinished = pyqtSignal()
    extractionError = pyqtSignal(str)
    
    def __init__(self, selected_items: List[Dict], output_base_dir: str):
        super().__init__()
        self.selected_items = selected_items
        self.output_base_dir = output_base_dir
        
    def run(self):
        try:
            from Core.lpk_loader import LpkLoader
            total_items = len(self.selected_items)
            
            for i, item in enumerate(self.selected_items):
                self.progressUpdated.emit(
                    int((i / total_items) * 100), 
                    f"Processing {item['title']}..."
                )
                
                # Create output directory for this item
                item_output_dir = os.path.join(self.output_base_dir, item['title'])
                os.makedirs(item_output_dir, exist_ok=True)
                
                # Process each LPK file in the item
                for lpk_file in item['lpk_files']:
                    config_file = item['config_files'][0] if item['config_files'] else None
                    
                    try:
                        loader = LpkLoader(lpk_file, config_file)
                        loader.extract(item_output_dir)
                    except Exception as e:
                        logging.error(f"Failed to extract {lpk_file}: {e}")
                        continue
            
            self.progressUpdated.emit(100, "Extraction completed!")
            self.extractionFinished.emit()
            
        except Exception as e:
            self.extractionError.emit(str(e))

class WorkshopItemCard(CardWidget):
    """Custom card widget for workshop items"""
    
    def __init__(self, item_data: Dict, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.selected = False
        self.setupUI()
        
    def setupUI(self):
        self.setFixedHeight(140)  # Increased height to accommodate preview image
        layout = QHBoxLayout(self)  # Changed to horizontal layout
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Preview image section
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(100, 100)
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                background-color: #F5F5F5;
            }
        """)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setScaledContents(True)
        
        # Load preview image if available
        self.load_preview_image()
        
        layout.addWidget(self.preview_label)
        
        # Content section
        content_layout = QVBoxLayout()
        content_layout.setSpacing(8)
        
        # Header with checkbox and title
        header_layout = QHBoxLayout()
        self.checkbox = CheckBox()
        self.checkbox.stateChanged.connect(self.on_selection_changed)
        
        self.title_label = SubtitleLabel(self.item_data['title'])
        self.title_label.setWordWrap(True)
        
        header_layout.addWidget(self.checkbox)
        header_layout.addWidget(self.title_label, 1)
        
        # Info layout
        info_layout = QGridLayout()
        info_layout.setSpacing(5)
        
        # Item ID
        info_layout.addWidget(BodyLabel("Item ID:"), 0, 0)
        info_layout.addWidget(CaptionLabel(self.item_data['item_id']), 0, 1)
        
        # LPK files count
        lpk_count = len(self.item_data['lpk_files'])
        info_layout.addWidget(BodyLabel("LPK Files:"), 1, 0)
        info_layout.addWidget(CaptionLabel(str(lpk_count)), 1, 1)
        
        # Size
        size_text = self.format_size(self.item_data['size'])
        info_layout.addWidget(BodyLabel("Size:"), 0, 2)
        info_layout.addWidget(CaptionLabel(size_text), 0, 3)
        
        # Config files
        config_count = len(self.item_data['config_files'])
        info_layout.addWidget(BodyLabel("Config Files:"), 1, 2)
        info_layout.addWidget(CaptionLabel(str(config_count)), 1, 3)
        
        content_layout.addLayout(header_layout)
        content_layout.addLayout(info_layout)
        
        layout.addLayout(content_layout, 1)  # Give content more space
        
    def load_preview_image(self):
        """Load and display preview image"""
        preview_path = self.item_data.get('preview_image')
        
        if preview_path and os.path.exists(preview_path):
            try:
                pixmap = QPixmap(preview_path)
                if not pixmap.isNull():
                    # Scale the image to fit the label while maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(
                        self.preview_label.size(), 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.preview_label.setPixmap(scaled_pixmap)
                else:
                    self.set_no_preview_text()
            except Exception as e:
                logging.debug(f"Failed to load preview image {preview_path}: {e}")
                self.set_no_preview_text()
        else:
            self.set_no_preview_text()
    
    def set_no_preview_text(self):
        """Set text when no preview image is available"""
        self.preview_label.setText("No Preview\nAvailable")
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                background-color: #F5F5F5;
                color: #888888;
                font-size: 12px;
            }
        """)
        
    def format_size(self, size_bytes: int) -> str:
        """Format size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def on_selection_changed(self, state):
        self.selected = state == Qt.Checked
        if hasattr(self.parent(), 'update_selection_count'):
            self.parent().update_selection_count()
    
    def is_selected(self) -> bool:
        return self.checkbox.isChecked()
    
    def set_selected(self, selected: bool):
        self.checkbox.setChecked(selected)

class SteamWorkshopPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('steamWorkshopPage')
        
        self.steam_integration = SteamIntegration()
        self.settings_manager = SettingsManager()
        self.workshop_items = []
        self.item_cards = []
        
        self.setupUI()
        self.configure_logging()
        
        # Auto-detect Steam on startup
        if self.settings_manager.get("auto_detect_steam", True):
            QTimer.singleShot(1000, self.auto_detect_steam)
        
    def setupUI(self):
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        # Add title
        self.title_label = SubtitleLabel("Steam Workshop Manager", self)
        self.main_layout.addWidget(self.title_label)
        
        # Steam path selection
        steam_layout = QHBoxLayout()
        self.steam_label = BodyLabel("Steam Path:", self)
        self.steam_edit = LineEdit(self)
        self.steam_edit.setPlaceholderText("Select Steam installation directory...")
        self.steam_browse_btn = PushButton("Browse", self)
        self.steam_browse_btn.clicked.connect(self.browse_steam_path)
        
        steam_layout.addWidget(self.steam_label)
        steam_layout.addWidget(self.steam_edit, 1)
        steam_layout.addWidget(self.steam_browse_btn)
        
        self.main_layout.addLayout(steam_layout)
        
        # Control buttons
        control_layout = QHBoxLayout()
        self.scan_btn = PushButton("Scan Workshop", self)
        self.scan_btn.setIcon(FluentIcon.SEARCH)
        self.scan_btn.clicked.connect(self.scan_workshop)
        
        self.select_all_btn = PushButton("Select All", self)
        self.select_all_btn.clicked.connect(self.select_all_items)
        self.select_all_btn.setEnabled(False)
        
        self.select_none_btn = PushButton("Select None", self)
        self.select_none_btn.clicked.connect(self.select_no_items)
        self.select_none_btn.setEnabled(False)
        
        self.extract_selected_btn = PushButton("Extract Selected", self)
        self.extract_selected_btn.setIcon(FluentIcon.DOWNLOAD)
        self.extract_selected_btn.clicked.connect(self.extract_selected)
        self.extract_selected_btn.setEnabled(False)
        
        control_layout.addWidget(self.scan_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.select_all_btn)
        control_layout.addWidget(self.select_none_btn)
        control_layout.addWidget(self.extract_selected_btn)
        
        self.main_layout.addLayout(control_layout)
        
        # Status label
        self.status_label = CaptionLabel("Ready to scan Steam Workshop", self)
        self.main_layout.addWidget(self.status_label)
        
        # Workshop items container (scrollable)
        from qfluentwidgets import ScrollArea
        self.scroll_area = ScrollArea(self)
        self.scroll_widget = QWidget()
        self.items_layout = QVBoxLayout(self.scroll_widget)
        self.items_layout.setSpacing(10)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        
        self.main_layout.addWidget(self.scroll_area, 1)
        
        # Progress bar
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)
        
        # Log output
        self.log_output = TextEdit(self)
        self.log_output.setMaximumHeight(150)
        self.main_layout.addWidget(self.log_output)
        
        # Load saved Steam path
        saved_steam_path = self.settings_manager.get("steam_path", "")
        if saved_steam_path and os.path.exists(saved_steam_path):
            self.steam_edit.setText(saved_steam_path)
    
    def configure_logging(self):
        """Configure logging to display in the text widget"""
        self.log_handler = QTextEditLogger(self.log_output)
        self.log_handler.setLevel(logging.INFO)
        
        # Add handler to relevant loggers
        loggers = [
            logging.getLogger("SteamIntegration"),
            logging.getLogger("lpkLoder"),
            logging.getLogger("SteamWorkshopPage")
        ]
        
        for logger in loggers:
            logger.addHandler(self.log_handler)
            logger.setLevel(logging.INFO)
    
    def auto_detect_steam(self):
        """Auto-detect Steam installation"""
        if not self.steam_edit.text():
            steam_path = self.steam_integration.find_steam_installation()
            if steam_path:
                self.steam_edit.setText(steam_path)
                self.settings_manager.set("steam_path", steam_path)
                self.status_label.setText(f"Auto-detected Steam at: {steam_path}")
    
    def browse_steam_path(self):
        """Browse for Steam installation directory"""
        steam_path = QFileDialog.getExistingDirectory(
            self, "Select Steam Installation Directory", 
            self.steam_edit.text() or "C:\\"
        )
        
        if steam_path:
            self.steam_edit.setText(steam_path)
            self.settings_manager.set("steam_path", steam_path)
    
    def scan_workshop(self):
        """Start scanning Steam Workshop"""
        steam_path = self.steam_edit.text().strip()
        
        if not steam_path:
            InfoBar.error(
                title="Error",
                content="Please select Steam installation directory first",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        if not os.path.exists(steam_path):
            InfoBar.error(
                title="Error", 
                content="Steam directory does not exist",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        # Start scanning in background thread
        self.scan_btn.setEnabled(False)
        self.status_label.setText("Scanning Steam Workshop...")
        
        self.scan_thread = SteamScanThread(steam_path)
        self.scan_thread.scanFinished.connect(self.on_scan_finished)
        self.scan_thread.scanError.connect(self.on_scan_error)
        self.scan_thread.start()
    
    def on_scan_finished(self, workshop_items: List[Dict]):
        """Handle scan completion"""
        self.workshop_items = workshop_items
        self.display_workshop_items()
        
        self.scan_btn.setEnabled(True)
        self.status_label.setText(f"Found {len(workshop_items)} workshop items")
        
        if workshop_items:
            self.select_all_btn.setEnabled(True)
            self.select_none_btn.setEnabled(True)
            self.extract_selected_btn.setEnabled(True)
    
    def on_scan_error(self, error_message: str):
        """Handle scan error"""
        self.scan_btn.setEnabled(True)
        self.status_label.setText("Scan failed")
        
        InfoBar.error(
            title="Scan Error",
            content=error_message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
    
    def display_workshop_items(self):
        """Display workshop items in the UI"""
        # Clear existing items
        for card in self.item_cards:
            card.setParent(None)
        self.item_cards.clear()
        
        # Add new items
        for item in self.workshop_items:
            card = WorkshopItemCard(item, self.scroll_widget)
            self.item_cards.append(card)
            self.items_layout.addWidget(card)
        
        # Add stretch to push items to top
        self.items_layout.addStretch()
    
    def select_all_items(self):
        """Select all workshop items"""
        for card in self.item_cards:
            card.set_selected(True)
        self.update_selection_count()
    
    def select_no_items(self):
        """Deselect all workshop items"""
        for card in self.item_cards:
            card.set_selected(False)
        self.update_selection_count()
    
    def update_selection_count(self):
        """Update selection count in status"""
        selected_count = sum(1 for card in self.item_cards if card.is_selected())
        total_count = len(self.item_cards)
        self.status_label.setText(f"Selected {selected_count} of {total_count} items")
    
    def extract_selected(self):
        """Extract selected workshop items"""
        selected_items = [
            card.item_data for card in self.item_cards if card.is_selected()
        ]
        
        if not selected_items:
            InfoBar.warning(
                title="No Selection",
                content="Please select at least one item to extract",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        # Choose output directory
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory",
            self.settings_manager.get("last_output_path", os.getcwd())
        )
        
        if not output_dir:
            return
        
        self.settings_manager.set("last_output_path", output_dir)
        
        # Start extraction
        self.start_batch_extraction(selected_items, output_dir)
    
    def start_batch_extraction(self, selected_items: List[Dict], output_dir: str):
        """Start batch extraction process"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.extract_selected_btn.setEnabled(False)
        
        self.extraction_thread = BatchExtractionThread(selected_items, output_dir)
        self.extraction_thread.progressUpdated.connect(self.on_extraction_progress)
        self.extraction_thread.extractionFinished.connect(self.on_extraction_finished)
        self.extraction_thread.extractionError.connect(self.on_extraction_error)
        self.extraction_thread.start()
    
    def on_extraction_progress(self, progress: int, message: str):
        """Handle extraction progress update"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
    
    def on_extraction_finished(self):
        """Handle extraction completion"""
        self.progress_bar.setVisible(False)
        self.extract_selected_btn.setEnabled(True)
        self.status_label.setText("Extraction completed successfully!")
        
        InfoBar.success(
            title="Success",
            content="All selected items have been extracted successfully",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
    
    def on_extraction_error(self, error_message: str):
        """Handle extraction error"""
        self.progress_bar.setVisible(False)
        self.extract_selected_btn.setEnabled(True)
        self.status_label.setText("Extraction failed")
        
        InfoBar.error(
            title="Extraction Error",
            content=error_message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
    
    def updateUIScale(self, window_width, window_height):
        """Update UI scaling based on window size"""
        # Adjust font sizes based on window size
        base_font_size = max(8, min(12, window_width // 100))
        
        font = QFont()
        font.setPointSize(base_font_size)
        
        # Apply to various elements
        self.title_label.setFont(font)
        self.status_label.setFont(font)