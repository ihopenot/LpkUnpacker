import os
import json
import logging
import winreg
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger("SteamIntegration")

class SteamIntegration:
    """Steam Workshop integration for automatic LPK discovery"""
    
    def __init__(self):
        self.steam_path = None
        self.workshop_path = None
        self.game_id = "616720"  # Girls' Frontline game ID
        
    def find_steam_installation(self) -> Optional[str]:
        """Find Steam installation path from registry"""
        try:
            # Try to find Steam installation path from registry
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
                steam_path = winreg.QueryValueEx(key, "InstallPath")[0]
                if os.path.exists(steam_path):
                    self.steam_path = steam_path
                    logger.info(f"Found Steam installation at: {steam_path}")
                    return steam_path
        except (FileNotFoundError, OSError, winreg.error):
            pass
            
        # Try common installation paths
        common_paths = [
            r"C:\Program Files (x86)\Steam",
            r"C:\Program Files\Steam",
            r"D:\Steam",
            r"E:\Steam"
        ]
        
        for path in common_paths:
            if os.path.exists(os.path.join(path, "steam.exe")):
                self.steam_path = path
                logger.info(f"Found Steam installation at: {path}")
                return path
                
        logger.warning("Steam installation not found")
        return None
    
    def get_workshop_path(self, steam_path: str = None) -> Optional[str]:
        """Get workshop path for the game"""
        if steam_path is None:
            steam_path = self.steam_path or self.find_steam_installation()
            
        if not steam_path:
            return None
            
        workshop_path = os.path.join(steam_path, "steamapps", "workshop", "content", self.game_id)
        
        if os.path.exists(workshop_path):
            self.workshop_path = workshop_path
            logger.info(f"Found workshop path: {workshop_path}")
            return workshop_path
        else:
            logger.warning(f"Workshop path not found: {workshop_path}")
            return None
    
    def scan_workshop_items(self, workshop_path: str = None) -> List[Dict]:
        """Scan workshop directory for LPK files"""
        if workshop_path is None:
            workshop_path = self.workshop_path or self.get_workshop_path()
            
        if not workshop_path or not os.path.exists(workshop_path):
            logger.warning("Workshop path not available")
            return []
            
        workshop_items = []
        
        try:
            for item_id in os.listdir(workshop_path):
                item_path = os.path.join(workshop_path, item_id)
                if not os.path.isdir(item_path):
                    continue
                    
                # Look for LPK files in the item directory
                lpk_files = []
                config_files = []
                
                for root, dirs, files in os.walk(item_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if file.lower().endswith('.lpk'):
                            lpk_files.append(file_path)
                        elif file.lower() == 'config.json':
                            config_files.append(file_path)
                
                if lpk_files:
                    # Try to get workshop item info
                    item_info = self.get_workshop_item_info(item_id, item_path)
                    
                    workshop_items.append({
                        'item_id': item_id,
                        'item_path': item_path,
                        'lpk_files': lpk_files,
                        'config_files': config_files,
                        'title': item_info.get('title', f'Workshop Item {item_id}'),
                        'description': item_info.get('description', ''),
                        'size': self.get_directory_size(item_path)
                    })
                    
        except Exception as e:
            logger.error(f"Error scanning workshop items: {e}")
            
        logger.info(f"Found {len(workshop_items)} workshop items with LPK files")
        return workshop_items
    
    def get_workshop_item_info(self, item_id: str, item_path: str) -> Dict:
        """Get workshop item information from Steam files"""
        info = {'title': f'Workshop Item {item_id}', 'description': ''}
        
        # Try to read workshop item info from Steam's appworkshop file
        if self.steam_path:
            appworkshop_path = os.path.join(
                self.steam_path, "steamapps", "workshop", f"appworkshop_{self.game_id}.acf"
            )
            
            if os.path.exists(appworkshop_path):
                try:
                    with open(appworkshop_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Simple parsing for workshop item info
                        if item_id in content:
                            # This is a simplified approach - Steam's ACF format is more complex
                            info['title'] = f'Workshop Item {item_id}'
                except Exception as e:
                    logger.debug(f"Could not read workshop info: {e}")
        
        # Try to find a description file in the item directory
        desc_files = ['description.txt', 'readme.txt', 'info.txt']
        for desc_file in desc_files:
            desc_path = os.path.join(item_path, desc_file)
            if os.path.exists(desc_path):
                try:
                    with open(desc_path, 'r', encoding='utf-8', errors='ignore') as f:
                        info['description'] = f.read()[:200] + '...' if len(f.read()) > 200 else f.read()
                        break
                except Exception:
                    pass
        
        return info
    
    def get_directory_size(self, path: str) -> int:
        """Get total size of directory in bytes"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            logger.debug(f"Could not calculate directory size: {e}")
        return total_size
    
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
    
    def get_recommended_output_path(self, item_title: str) -> str:
        """Get recommended output path for extracted files"""
        # Clean the title for use as directory name
        clean_title = "".join(c for c in item_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_title = clean_title.replace(' ', '_')
        
        output_dir = os.path.join(os.getcwd(), "extracted", clean_title)
        return output_dir