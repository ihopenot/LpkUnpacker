from hashlib import md5
import os
import re
import json
import filetype
from filetype.types import Type

def hashed_filename(s: str) -> str:
    t = md5()
    t.update(s.encode())
    return t.hexdigest()

def safe_mkdir(s: str):
    try:
        os.mkdir(s)
    except FileExistsError:
        pass

def genkey(s: str) -> int:
    ret = 0
    for i in s:
        ret = (ret * 31 + ord(i)) & 0xffffffff
    if ret & 0x80000000:
        ret = ret | 0xffffffff00000000
    return ret

def decrypt(key: int, data: bytes) -> bytes:
    ret = []
    for slice in [data[i:i+1024] for i in range(0, len(data), 1024)]:
        tmpkey = key
        for i in slice:
            tmpkey = (65535 & 2531011 + 214013 * tmpkey >> 16) & 0xffffffff
            ret.append((tmpkey & 0xff) ^ i)
    return bytes(ret)

match_rule = re.compile(r"[0-9a-f]{32}.bin3?")
def is_encrypted_file(s: str) -> bool:
    if type(s) != str:
        return False
    if match_rule.fullmatch(s) != None:
        return True
    return False

# find all enc_file in s
def find_encrypted_file(s: str) -> str:
    files = re.findall(match_rule, s)
    if files == []:
        return None
    return files[0]

def get_encrypted_file(s: str):
    if type(s) != str:
        return None
    if s.startswith("change_cos"):
        filename = s[len("change_cos "):]
    else:
        filename = s
    if not is_encrypted_file(filename):
        return None
    return filename


def travels_dict(dic: dict):
    for k in dic:
        if type(dic[k]) == dict:
            for p, v in travels_dict(dic[k]):
                yield f"{k}_{p}", v
        elif type(dic[k]) == list:
            for p, v in travels_list(dic[k]):
                yield f"{k}_{p}", v
        else:
            yield str(k), dic[k]
        
def travels_list(vals: list):
    for i in range(len(vals)):
        if type(vals[i]) == dict:
            for p, v in travels_dict(vals[i]):
                yield f"{i}_{p}", v
        elif type(vals[i]) == list:
            for p, v in travels_list(vals[i]):
                yield f"{i}_{p}", v
        else:
            yield str(i), vals[i]


class Moc3(Type):
    MIME = "application/moc3"
    EXTENSION = "moc3"
    def __init__(self):
        super(Moc3, self).__init__(mime=Moc3.MIME, extension=Moc3.EXTENSION)
    
    def match(self, buf):
        return len(buf) > 3 and buf.startswith(b"MOC3")

class Moc(Type):
    MIME = "application/moc"
    EXTENSION = "moc"
    def __init__(self):
        super(Moc, self).__init__(mime=Moc.MIME, extension=Moc.EXTENSION)
    
    def match(self, buf):
        return len(buf) > 3 and buf.startswith(b"moc")

filetype.add_type(Moc3())
filetype.add_type(Moc())

def guess_type(data: bytes):
    ftype = filetype.guess(data)
    if ftype != None:
        return "." + ftype.extension
    try:
        json.loads(data.decode("utf8"))
        return ".json"
    except:
        return ""