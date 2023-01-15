import sys
import argparse
from Core.lpk_loader import *
from Core.utils import *

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbosity", action="count", default=0, help="increase output verbosity")
parser.add_argument("-c", "--config", help="config.json")
parser.add_argument("target_lpk", help="path to lpk file")
parser.add_argument("output_dir", help="directory to store result")
loglevels = ["FATAL", "INFO", "DEBUG"]

if __name__ == "__main__":
    args = parser.parse_args()

    verbosity = args.verbosity if args.verbosity < len(loglevels) else len(loglevels) -1
    loglevel=loglevels[verbosity]

    logging.basicConfig(level=loglevel, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    loader = LpkLoader(args.target_lpk, args.config)

    loader.extract(args.output_dir)
