# LpkUnpacker
English/[中文](https://github.com/ihopenot/LpkUnpacker/blob/master/README.md)

This tool is designed to extract resources from Live2dExViewer's LPK files.

If you encounter any issues while running this program, please consult the '[Issues](https://github.com/ihopenot/LpkUnpacker/issues)' section first.

*Added support for (pre-)STD_1_0 formats.
However, not all packs can be decrypted due to an unknown keygen/decryption algorithm.

## Usage

You can download the GUI executable from the [release](https://github.com/ihopenot/LpkUnpacker/releases) page, or run it directly from the source code.

![Guide Animation](Img/Guide.gif)

### Requirements
`python -m pip install -r requirements.txt`

### GUI
```
python LpkUnpackerGUI.py
```

### Cmdline
```
usage: LpkUnpacker.py [-h] [-v] [-c CONFIG] target_lpk output_dir

positional arguments:
  target_lpk            path to lpk file
  output_dir            directory to store result

options:
  -h, --help            show this help message and exit
  -v, --verbosity       increase output verbosity
  -c CONFIG, --config CONFIG
                        config.json
```

## Compile

The release executable was compiled with Nuitka. To compile it yourself, use the following commands.

1. install requirements
```
pip install nuitka
```

2. Compile
```
compile.bat
```

The compiled file will be saved in the `build` directory.

## Notice

Steam workshop .lpk file needs config.json to decrypt.

.lpk file can be found at 

`path/to/your/steam/steamapps/workshop/content/616720/...` 

or 

`path/to/your/steam/steamapps/common/Live2DViewerEX/shared/workshop/...`


To decrypt .wpk file, you need to unzip it with 7zip or other unzip tools, and you will get .lpk file and config.json. 
