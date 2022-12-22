from __future__ import unicode_literals
from typing import Tuple
import zipfile
import json
from Core.utils import *

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
        if self.mlve_config["type"] == "STM_1_0":
            self.load_config()
    
    def load_config(self):
        self.config = json.loads(open(self.configpath, "r", encoding="utf8").read())

    def extract(self, outputdir: str):
        for chara in self.mlve_config["list"]:

            subdir = outputdir + (chara["character"] if chara["character"] != "" else "character") + "/"
            safe_mkdir(subdir)

            for i in range(len(chara["costume"])):
                self.extract_costume(chara["costume"][i], subdir, i)

            for name in self.entrys:
                out_s: str = self.entrys[name]
                for k in self.trans:
                    out_s = out_s.replace(k, self.trans[k])
                open(subdir+name, "w", encoding="utf8").write(out_s)
    
    def extract_costume(self, costume: list, dir: str, id: int):
        subdir = dir
        if costume["path"] == "":
            return

        filename :str = costume["path"]

        try:
            entry_s = self.decrypt_file(filename).decode(encoding="utf8")
        except UnicodeDecodeError:
            print("tring to auto fix fileId")
            success = False
            possible_fileId = []
            possible_fileId.append(self.config["lpkFile"].strip('.lpk'))
            for fileid in possible_fileId:
                self.config["fileId"] = fileid
                try:
                    entry_s = self.decrypt_file(filename).decode(encoding="utf8")
                except UnicodeDecodeError:
                    continue

                success = True
                break
            if not success:
                print("steam workshop fileid is usually a foler under PATH_TO_YOUR_STEAM/steamapps/workshop/content/616720/([0-9]+)")
                fileid = input("auto fix failed, please input fileid manually: ")
                self.config["fileId"] = fileid
                try:
                    entry_s = self.decrypt_file(filename).decode(encoding="utf8")
                except UnicodeDecodeError:
                    print("decrypt failed")
                    exit(0)

        entry = json.loads(entry_s)

        for name, val in travels_dict(entry):
            if type(val) == str and is_encrypted_file(val):
                if val in self.trans:
                    continue
                name += f"_{id}"
                _, suffix = self.recovery(val, subdir + name)
                self.trans[val] = name + suffix

        self.trans[costume["path"]] = f"model{id}.json"

        out_s = json.dumps(entry, ensure_ascii=False)
        self.entrys[f"model{id}.json"] = out_s

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