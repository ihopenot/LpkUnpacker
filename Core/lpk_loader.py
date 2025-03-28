from __future__ import unicode_literals
from typing import Tuple
import zipfile
import json
from Core.utils import *
import logging
import os

logger = logging.getLogger("lpkLoder")

class LpkLoader():
    def __init__(self, lpkpath, configpath) -> None:
        self.lpkpath = lpkpath
        self.configpath = configpath
        self.lpkType = None
        self.encrypted = "true"
        self.trans = {}
        self.entrys = {}
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
    
    def extract(self, outputdir: str):
        if self.lpkType in ["STD2_0", "STM_1_0"]:
            for chara in self.mlve_config["list"]:
                if self.lpkType == "STM_1_0" and hasattr(self, 'config') and 'title' in self.config:
                    chara_name = self.config["title"]
                else:
                    chara_name = chara["character"] if chara["character"] != "" else "character"
                subdir =  os.path.join(outputdir, chara_name)
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

        out_s = json.dumps(entry, ensure_ascii=False)
        id = len(self.entrys)

        self.entrys[f"model{id}.json"] = out_s

        self.trans[model_json] = f"model{id}.json"

        logger.debug(f"model{id}.json:\n{entry}")

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
                        name += f"_{id}"
                        name = self.name_change(name)
                        _, suffix = self.recovery(enc_file, os.path.join(subdir, name))
                        self.trans[enc_file] = name + suffix


            if is_encrypted_file(val):
                enc_file = val
                # already decrypted
                if enc_file in self.trans:
                    continue
                # recover regular files
                else:
                    name += f"_{id}"
                    name = self.name_change(name)
                    _, suffix = self.recovery(enc_file, os.path.join(subdir, name))
                    self.trans[enc_file] = name + suffix
        
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
        ret = self.decrypt_file(filename)
        suffix = guess_type(ret)
        print(f"recovering {filename} -> {output+suffix}")
        open(output + suffix, "wb").write(ret)
        return ret, suffix

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
    
    def name_change(self, name: str) -> str:
        #去除name里面的FileReferences_
        name = name.replace("FileReferences_", "")
        return name.replace("\\", "/")