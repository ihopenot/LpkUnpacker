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
        if steam_path is None:
            steam_path = self.steam_path or self.find_steam_installation()
        if not steam_path:
            return None

        primary = os.path.join(steam_path, "steamapps", "workshop", "content", self.game_id)
        if os.path.exists(primary):
            self.workshop_path = primary
            logger.info(f"Found workshop path: {primary}")
            return primary

        for lib in self._get_library_paths(steam_path):
            candidate = os.path.join(lib, "workshop", "content", self.game_id)
            if os.path.exists(candidate):
                self.workshop_path = candidate
                logger.info(f"Found workshop path: {candidate}")
                return candidate

        shared = os.path.join(steam_path, "steamapps", "common", "Live2DViewerEX", "shared", "workshop")
        if os.path.exists(shared):
            self.workshop_path = shared
            logger.info(f"Found workshop path: {shared}")
            return shared

        logger.warning(f"Workshop path not found: {primary}")
        return None

    def _get_library_paths(self, steam_path: str) -> List[str]:
        libs = []
        vdf = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
        if not os.path.exists(vdf):
            return libs
        try:
            with open(vdf, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            for line in content.splitlines():
                line = line.strip()
                if '"path"' in line:
                    parts = line.split('"')
                    if len(parts) >= 4:
                        p = parts[3]
                        if os.path.exists(p):
                            libs.append(os.path.join(p, "steamapps"))
                else:
                    tokens = line.split('"')
                    if len(tokens) >= 3 and tokens[1].isdigit():
                        p = tokens[2].strip()
                        if p and os.path.exists(p):
                            libs.append(os.path.join(p, "steamapps"))
        except Exception:
            pass
        return libs
    
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
                    
                    # Search for preview images
                    preview_image = self.find_preview_image(item_path)
                    
                    workshop_items.append({
                        'item_id': item_id,
                        'item_path': item_path,
                        'lpk_files': lpk_files,
                        'config_files': config_files,
                        'title': item_info.get('title', f'Workshop Item {item_id}'),
                        'description': item_info.get('description', ''),
                        'size': self.get_directory_size(item_path),
                        'preview_image': preview_image
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
                        content = f.read()
                        info['description'] = (content[:200] + '...') if len(content) > 200 else content
                        break
                except Exception:
                    pass
        
        return info
    
    def find_preview_image(self, item_path: str) -> Optional[str]:
        """Find preview image in workshop item directory"""
        # Common preview image names and extensions
        preview_names = [
            'preview', 'thumbnail', 'icon', 'cover', 'image', 
            'screenshot', 'pic', 'photo', 'img'
        ]
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        
        try:
            # Search in the root directory first
            for file in os.listdir(item_path):
                file_lower = file.lower()
                file_path = os.path.join(item_path, file)
                
                # Check if it's an image file
                if any(file_lower.endswith(ext) for ext in image_extensions):
                    # Check if filename contains preview-related keywords
                    if any(name in file_lower for name in preview_names):
                        if os.path.isfile(file_path):
                            logger.debug(f"Found preview image: {file_path}")
                            return file_path
            
            # If no preview found in root, search subdirectories (limited depth)
            for root, dirs, files in os.walk(item_path):
                # Limit search depth to avoid performance issues
                depth = root[len(item_path):].count(os.sep)
                if depth >= 2:
                    dirs[:] = []  # Don't go deeper
                    continue
                    
                for file in files:
                    file_lower = file.lower()
                    file_path = os.path.join(root, file)
                    
                    # Check if it's an image file with preview-related name
                    if any(file_lower.endswith(ext) for ext in image_extensions):
                        if any(name in file_lower for name in preview_names):
                            logger.debug(f"Found preview image in subdirectory: {file_path}")
                            return file_path
            
            # If still no preview found, return the first image file found
            for root, dirs, files in os.walk(item_path):
                depth = root[len(item_path):].count(os.sep)
                if depth >= 2:
                    dirs[:] = []
                    continue
                    
                for file in files:
                    file_lower = file.lower()
                    if any(file_lower.endswith(ext) for ext in image_extensions):
                        file_path = os.path.join(root, file)
                        logger.debug(f"Using first available image as preview: {file_path}")
                        return file_path
                        
        except Exception as e:
            logger.debug(f"Error searching for preview image in {item_path}: {e}")
            
        return None
    
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