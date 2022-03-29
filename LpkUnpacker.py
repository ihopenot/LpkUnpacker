import sys
from Core.lpk_loader import *
from Core.utils import *

if __name__ == "__main__":
    try:
        lpkpath = sys.argv[1]
        outputdir = sys.argv[2]
        if len(sys.argv) > 3:
            configpath = sys.argv[3]
        else:
            configpath = None
    except:
        print(f"usage:\n\t{__file__} target.lpk outputdir [config.json]")
        exit(0)
    
    loader = LpkLoader(lpkpath, configpath)

    if not outputdir.endswith("/"):
        outputdir = outputdir + "/"
    loader.extract(outputdir)
