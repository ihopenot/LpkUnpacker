import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("SettingsManager")

class SettingsManager:
    """Manages application settings and user preferences"""
    
    def __init__(self, settings_file: str = "settings.json"):
        self.settings_file = os.path.join(os.getcwd(), settings_file)
        self.settings = self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file"""
        default_settings = {
            "last_lpk_path": "",
            "last_config_path": "",
            "last_output_path": os.path.join(os.getcwd(), "output"),
            "steam_path": "",
            "auto_detect_steam": True,
            "remember_paths": True,
            "theme": "auto",
            "language": "zh_CN",
            "window_geometry": {
                "width": 1000,
                "height": 700,
                "x": 100,
                "y": 100
            },
            "extraction_settings": {
                "create_subfolders": True,
                "overwrite_existing": False,
                "log_level": "INFO"
            }
        }
        
        if not os.path.exists(self.settings_file):
            logger.info("Settings file not found, using defaults")
            return default_settings
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                for key, value in default_settings.items():
                    if key not in loaded_settings:
                        loaded_settings[key] = value
                return loaded_settings
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return default_settings
    
    def save_settings(self) -> bool:
        """Save current settings to file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            logger.debug("Settings saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        keys = key.split('.')
        value = self.settings
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value"""
        keys = key.split('.')
        setting = self.settings
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in setting:
                setting[k] = {}
            setting = setting[k]
        
        # Set the value
        setting[keys[-1]] = value
        
        # Auto-save if remember_paths is enabled
        if self.get("remember_paths", True):
            self.save_settings()
    
    def update_last_paths(self, lpk_path: str = None, config_path: str = None, output_path: str = None):
        """Update last used paths"""
        if not self.get("remember_paths", True):
            return
            
        if lpk_path:
            self.set("last_lpk_path", lpk_path)
        if config_path:
            self.set("last_config_path", config_path)
        if output_path:
            self.set("last_output_path", output_path)
    
    def update_window_geometry(self, width: int, height: int, x: int, y: int):
        """Update window geometry"""
        self.set("window_geometry.width", width)
        self.set("window_geometry.height", height)
        self.set("window_geometry.x", x)
        self.set("window_geometry.y", y)
    
    def get_recent_files(self, max_count: int = 10) -> list:
        """Get list of recently used files"""
        recent = self.get("recent_files", [])
        return recent[:max_count]
    
    def add_recent_file(self, file_path: str, file_type: str = "lpk"):
        """Add a file to recent files list"""
        recent = self.get("recent_files", [])
        
        # Remove if already exists
        recent = [item for item in recent if item.get("path") != file_path]
        
        # Add to beginning
        recent.insert(0, {
            "path": file_path,
            "type": file_type,
            "timestamp": self._get_timestamp()
        })
        
        # Limit to 10 items
        recent = recent[:10]
        
        self.set("recent_files", recent)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as string"""
        import datetime
        return datetime.datetime.now().isoformat()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = self.load_settings()
        # Force reload defaults by removing the file temporarily
        if os.path.exists(self.settings_file):
            os.remove(self.settings_file)
        self.settings = self.load_settings()
        self.save_settings()
        logger.info("Settings reset to defaults")