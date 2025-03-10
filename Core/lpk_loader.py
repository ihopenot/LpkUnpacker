from __future__ import unicode_literals
from typing import Tuple
import zipfile
import json
from Core.utils import *
import logging
import os
import re

logger = logging.getLogger("lpkLoder")

class LpkLoader():
    def __init__(self, lpkpath, configpath) -> None:
        # Convert to absolute paths immediately 
        self.lpkpath = os.path.abspath(lpkpath) if lpkpath else None
        self.configpath = os.path.abspath(configpath) if configpath else None
        self.lpkType = None
        self.encrypted = "true"
        self.trans = {}
        self.entrys = {}
        self.title = None
        self.load_lpk()
    
    def load_lpk(self):
        self.lpkfile = zipfile.ZipFile(self.lpkpath)
        try:
            config_mlve_raw = self.lpkfile.read(hashed_filename("config.mlve")).decode()
        except KeyError:
            try:
                config_mlve_raw = self.lpkfile.read("config.mlve").decode('utf-8-sig')
            except:
                logger.fatal("Failed to retrieve lpk config!")
                exit(0)


        self.mlve_config = json.loads(config_mlve_raw)

        logger.debug(f"mlve config:\n {self.mlve_config}")
        self.lpkType = self.mlve_config.get("type")
        # only steam workshop lpk needs config.json to decrypt
        if self.lpkType == "STM_1_0":
            self.load_config()
    
    def load_config(self):
        self.config = json.loads(open(self.configpath, "r", encoding="utf8").read())
        # Extract title from config if available
        if "title" in self.config:
            self.title = self.config["title"]
            # Clean title for use as folder name
            self.title = self.sanitize_filename(self.title)

    def sanitize_filename(self, filename):
        """
        Remove characters that are invalid in Windows filenames
        and ensure no control characters remain
        """
        # First remove any control characters (including \r)
        filename = ''.join(c for c in filename if ord(c) >= 32 or c == ' ')
        
        # Remove characters that are invalid in Windows filenames
        invalid_chars = r'[<>:"/\\|?*]'
        clean_name = re.sub(invalid_chars, '', filename)
        
        # Limit length to avoid path issues
        if len(clean_name) > 100:
            clean_name = clean_name[:100]
        
        # If empty after cleaning, use default
        if not clean_name.strip():
            clean_name = "untitled"
        
        return clean_name

    def extract(self, outputdir: str):
        # Always convert to absolute path for output
        outputdir = os.path.abspath(outputdir)
        
        # Use title from config as subdirectory if available
        if self.title:
            # Normalize and clean the path to avoid issues
            clean_title = self.sanitize_filename(self.title)
            outputdir = os.path.join(outputdir, clean_title)
            safe_mkdir(outputdir)
            print(f"Using title as output folder: {outputdir}")
        
        if self.lpkType in ["STD2_0", "STM_1_0"]:
            for chara in self.mlve_config["list"]:
                chara_name = chara["character"] if chara["character"] != "" else "character"
                subdir = outputdir
                safe_mkdir(subdir)
                for i in range(len(chara["costume"])):
                    logger.info(f"extracting {chara_name}_costume_{i}")
                    self.extract_costume(chara["costume"][i], subdir)

                # replace encryped filename to decrypted filename in entrys(model.json)
                for name in self.entrys:
                    out_s: str = self.entrys[name]
                    for k in self.trans:
                        out_s = out_s.replace(k, self.trans[k])
                    open(os.path.join(subdir, name), "w", encoding="utf8").write(out_s)
        else:
            try:
                print("Deprecated/unknown lpk format detected. Attempting with STD_1_0 format...")
                print("Decryption may not work for some packs, even though this script outputs all files.")
                self.encrypted = self.mlve_config.get("encrypt", "true")
                if self.encrypted == "false":
                    print("lpk is not encrypted, extracting all files...")
                    self.lpkfile.extractall(outputdir)
                    return
                # For STD_1_0 and earlier
                for file in self.lpkfile.namelist():
                    if os.path.splitext(file)[-1] == '':
                        continue
                    subdir = os.path.join(outputdir, os.path.dirname(file))
                    outputFilePath = os.path.join(subdir, os.path.basename(file))
                    safe_mkdir(subdir)
                    if os.path.splitext(file)[-1] in [".json", ".mlve", ".txt"]:
                        print(f"Extracting {file} -> {outputFilePath}")
                        self.lpkfile.extract(file, outputdir)
                    else:
                        print(f"Decrypting {file} -> {outputFilePath}")
                        decryptedData = self.decrypt_file(file)
                        with open(outputFilePath, "wb") as outputFile:
                            outputFile.write(decryptedData)
            except:
                logger.fatal(f"Failed to decrypt {self.lpkpath}, possibly wrong/unsupported format.")
                exit(0)
    
    def extract_costume(self, costume: dict, dir: str):
        if costume["path"] == "":
            return

        filename :str = costume["path"]

        self.check_decrypt(filename)

        self.extract_model_json(filename, dir)

    def extract_model_json(self, model_json: str, dir):
        logger.debug(f"========= extracting model {model_json} =========")
        # already extracted
        if model_json in self.trans:
            return

        subdir = dir
        entry_s = self.decrypt_file(model_json).decode(encoding="utf8")
        entry = json.loads(entry_s)

        # Update JSON references to use clean filenames
        self.clean_json_references(entry)
        
        out_s = json.dumps(entry, ensure_ascii=False)
        model_filename = "model.json"
        
        # Ensure unique model filenames
        counter = 0
        while os.path.exists(os.path.join(subdir, model_filename)):
            counter += 1
            model_filename = f"model_{counter}.json"
        
        self.entrys[model_filename] = out_s
        self.trans[model_json] = model_filename

        logger.debug(f"{model_filename}:\n{entry}")

        for name, val in travels_dict(entry):
            logger.debug(f"{name} -> {val}")
            # extract submodel
            if (name.lower().endswith("_command") or name.lower().endswith("_postcommand")) and val:
                commands = val.split(";")
                for cmd in commands:
                    enc_file = find_encrypted_file(cmd)
                    if enc_file == None:
                        continue

                    if cmd.startswith("change_cos"):
                        enc_file = find_encrypted_file(cmd)
                        self.extract_model_json(enc_file, dir)
                    else:
                        clean_name = self.clean_filename(name)
                        _, suffix = self.recovery(enc_file, os.path.join(subdir, clean_name))
                        self.trans[enc_file] = clean_name + suffix


            if is_encrypted_file(val):
                enc_file = val
                # already decrypted
                if enc_file in self.trans:
                    continue
                # recover regular files
                else:
                    clean_name = self.clean_filename(name)
                    _, suffix = self.recovery(enc_file, os.path.join(subdir, clean_name))
                    self.trans[enc_file] = clean_name + suffix
        
        logger.debug(f"========= end of model {model_json} =========")

    def check_decrypt(self, filename):
        '''
        Check if decryption work.

        If lpk earsed fileId in config.json, this function will automatically try to use lpkFile as fileId.
        If all attemptions failed, this function will read fileId from ``STDIN``.
        '''

        logger.info("try to decrypt entry model.json")

        try:
            self.decrypt_file(filename).decode(encoding="utf8")
        except UnicodeDecodeError:
            logger.info("trying to auto fix fileId")
            success = False
            possible_fileId = []
            possible_fileId.append(self.config["lpkFile"].strip('.lpk'))
            for fileid in possible_fileId:
                self.config["fileId"] = fileid
                try:
                    self.decrypt_file(filename).decode(encoding="utf8")
                except UnicodeDecodeError:
                    continue

                success = True
                break
            if not success:
                print("steam workshop fileid is usually a foler under PATH_TO_YOUR_STEAM/steamapps/workshop/content/616720/([0-9]+)")
                fileid = input("auto fix failed, please input fileid manually: ")
                self.config["fileId"] = fileid
                try:
                    self.decrypt_file(filename).decode(encoding="utf8")
                except UnicodeDecodeError:
                    logger.fatal("decrypt failed!")
                    exit(0)

    def recovery(self, filename, output) -> Tuple[bytes, str]:
        """
        Decrypt and save a file with the given filename to the output path
        Returns the decrypted data and file suffix
        """
        # Get the decrypted data
        ret = self.decrypt_file(filename)
        suffix = guess_type(ret)
        
        # Ensure output path uses forward slashes consistently
        output = output.replace('\\', '/')
        
        # Get just the directory and base filename
        dir_path = os.path.dirname(output)
        base_name = os.path.basename(output)
        
        # Clean the filename (remove prefixes/suffixes)
        clean_filename = self.clean_filename(base_name)
        
        # Ensure the file has a unique name
        final_filename = clean_filename
        counter = 0
        while os.path.exists(os.path.join(dir_path, final_filename) + suffix):
            counter += 1
            name_parts = os.path.splitext(clean_filename)
            final_filename = f"{name_parts[0]}_{counter}{name_parts[1]}"
        
        # Final file path
        final_path = os.path.join(dir_path, final_filename).replace('\\', '/')
        
        try:
            # Ensure the directory exists
            os.makedirs(dir_path, exist_ok=True)
            
            print(f"Recovering {filename} -> {final_path+suffix}")
            with open(final_path + suffix, "wb") as f:
                f.write(ret)
        except OSError as e:
            # If saving fails, use a simpler filename
            safe_name = f"file_{abs(hash(filename)) % 10000}{suffix}"
            safe_path = os.path.join(dir_path, safe_name).replace('\\', '/')
            print(f"Error with filename, using safe alternative: {safe_path}")
            
            try:
                os.makedirs(dir_path, exist_ok=True)
                with open(safe_path, "wb") as f:
                    f.write(ret)
                return ret, safe_name
            except OSError as e2:
                # Last resort: use the root output directory
                root_dir = os.path.dirname(os.path.dirname(dir_path))
                safe_path = os.path.join(root_dir, safe_name).replace('\\', '/')
                os.makedirs(root_dir, exist_ok=True)
                with open(safe_path, "wb") as f:
                    f.write(ret)
                return ret, safe_name
        
        return ret, suffix

    def clean_filename(self, filename):
        """
        Clean filenames by:
        1. Removing common prefixes like "FileReferences_"
        2. Removing patterns like "_File_0" or "_Sound_0" at the end
        3. Preserving important identifiers like "Motions_1_Tap"
        """
        # Remove common prefixes
        common_prefixes = [
            "FileReferences_",
        ]
        
        result = filename
        for prefix in common_prefixes:
            if result.startswith(prefix):
                result = result.replace(prefix, "", 1)
        
        # Split by extension
        base_name, ext = os.path.splitext(result)
        
        # Remove _File_X and _Sound_X patterns
        base_name = re.sub(r'_File_\d+$', '', base_name)
        base_name = re.sub(r'_Sound_\d+$', '', base_name)
        
        # Handle Motions_X_Type patterns specifically
        if "Motions_" in base_name:
            # Preserve the structure but remove unnecessary parts
            parts = base_name.split('_')
            cleaned_parts = []
            i = 0
            while i < len(parts):
                # Keep Motions_ prefix
                if parts[i] == "Motions":
                    cleaned_parts.append(parts[i])
                    
                # Keep the number after Motions_
                elif i > 0 and parts[i-1] == "Motions" and parts[i].isdigit():
                    cleaned_parts.append(parts[i])
                    
                # Keep the type (like Tap, Idle, etc.) but skip any File/Sound suffixes
                elif i > 1 and parts[i-2] == "Motions":
                    if parts[i] not in ["File", "Sound"]:
                        cleaned_parts.append(parts[i])
                    else:
                        # Skip both the File/Sound and the following number
                        i += 1
                        
                # Keep other important parts
                elif parts[i] not in ["File", "Sound"]:
                    cleaned_parts.append(parts[i])
                    
                i += 1
            
            base_name = "_".join(cleaned_parts)
        
        # Handle other cases
        else:
            # Remove numeric suffixes at the end of parts
            parts = base_name.split('_')
            cleaned_parts = []
            for i, part in enumerate(parts):
                if part not in ["File", "Sound"] and not (i < len(parts)-1 and parts[i+1].isdigit() and (part == "File" or part == "Sound")):
                    # Remove trailing numbers from the last part
                    if i == len(parts)-1:
                        part = re.sub(r'\d+$', '', part)
                    cleaned_parts.append(part)
            
            base_name = "_".join(cleaned_parts)
        
        return base_name + ext

    def clean_json_references(self, json_obj):
        """Clean references in JSON by removing common prefixes"""
        if isinstance(json_obj, dict):
            for key, value in list(json_obj.items()):
                if isinstance(value, (dict, list)):
                    self.clean_json_references(value)
                elif isinstance(value, str) and any(value.startswith(prefix) for prefix in ["FileReferences_"]):
                    json_obj[key] = self.clean_filename(value)
        elif isinstance(json_obj, list):
            for item in json_obj:
                if isinstance(item, (dict, list)):
                    self.clean_json_references(item)
                elif isinstance(item, str) and any(item.startswith(prefix) for prefix in ["FileReferences_"]):
                    index = json_obj.index(item)
                    json_obj[index] = self.clean_filename(item)

    def getkey(self, file: str):
        if self.lpkType == "STM_1_0" and self.mlve_config["encrypt"] != "true":
            return 0
        if self.lpkType == "STM_1_0":
            return genkey(self.mlve_config["id"] + self.config["fileId"] + file + self.config["metaData"])
        elif self.lpkType == "STD2_0":
            return genkey(self.mlve_config["id"] + file)
        elif self.lpkType == "STD_1_0":
            return genkey(self.mlve_config["id"] + file)
        else:
            #return genkey("com.oukaitou.live2d.pro" + self.mlve_config["id"] + "cDaNJnUazx2B4xCYFnAPiYSyd2M=\n")
        #else:
            raise Exception(f"not support type {self.mlve_config['type']}")

    def decrypt_file(self, filename) -> bytes:
        data = self.lpkfile.read(filename)
        return self.decrypt_data(filename, data)

    def decrypt_data(self, filename: str, data: bytes) -> bytes:
        key = self.getkey(filename)
        return decrypt(key, data)