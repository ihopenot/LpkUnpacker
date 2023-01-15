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
        self.trans = {}
        self.entrys = {}
        self.load_lpk()
    
    def load_lpk(self):
        self.lpkfile = zipfile.ZipFile(self.lpkpath)

        config_mlve_raw = self.lpkfile.read(hashed_filename("config.mlve")).decode()
        self.mlve_config = json.loads(config_mlve_raw)

        logger.debug(f"mlve config:\n {self.mlve_config}")

        # only steam workshop lpk needs config.json to decrypt
        if self.mlve_config["type"] == "STM_1_0":
            self.load_config()
    
    def load_config(self):
        self.config = json.loads(open(self.configpath, "r", encoding="utf8").read())

    def extract(self, outputdir: str):
        for chara in self.mlve_config["list"]:
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
    
    def extract_costume(self, costume: dict, dir: str):
        if costume["path"] == "":
            return

        filename :str = costume["path"]

        self.check_decrypt(filename)

        self.extract_model_json(filename, dir)

    def extract_model_json(self, model_json: str, dir):
        subdir = dir
        entry_s = self.decrypt_file(model_json).decode(encoding="utf8")
        entry = json.loads(entry_s)

        out_s = json.dumps(entry, ensure_ascii=False)
        id = len(self.entrys)

        self.entrys[f"model{id}.json"] = out_s

        self.trans[model_json] = f"model{id}.json"

        logger.debug(f"model{id}.json:\n{entry}")

        for name, val in travels_dict(entry):
            enc_file = get_encrypted_file(val)
            if enc_file:
                # already decrypted
                if enc_file in self.trans:
                    continue
                # extract submodel
                if val.startswith("change_cos"):
                    self.extract_model_json(enc_file, dir)
                # recover regular files
                else:
                    name += f"_{id}"
                    _, suffix = self.recovery(enc_file, os.path.join(subdir, name))
                    self.trans[enc_file] = name + suffix


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
        if self.mlve_config["type"] == "STM_1_0" and self.mlve_config["encrypt"] != "true":
            return 0

        if self.mlve_config["type"] == "STM_1_0":
            return genkey(self.mlve_config["id"] + self.config["fileId"] + file + self.config["metaData"])
        elif self.mlve_config["type"] == "STD2_0":
            return genkey(self.mlve_config["id"] + file)
        else:
            raise Exception(f"not support type {self.mlve_config['type']}")

    def decrypt_file(self, filename) -> bytes:
        data = self.lpkfile.read(filename)
        return self.decrypt_data(filename, data)

    def decrypt_data(self, filename: str, data: bytes) -> bytes:
        key = self.getkey(filename)
        return decrypt(key, data)