# LpkUnpacker
[English](https://github.com/ihopenot/LpkUnpacker/blob/master/README.md)/中文

这个工具用来解包Live2dViewerEx的LPK文件

如果你在使用工具时遇到任何困难，请先查询'[Issues](https://github.com/ihopenot/LpkUnpacker/issues)'中的内容

## 系统需求
安装依赖：

`python -m pip install -r requirements.txt`

## 使用说明
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

Steam创意工坊中的lpk文件通常需要config.json来解密

.lpk文件通常在下面这样的路径下

`path/to/your/steam/steamapps/workshop/content/616720/...` 或者 `path/to/your/steam/steamapps/common/Live2DViewerEX/shared/workshop/...`

如果要解密wpk文件，你需要先把它解压之后得到lpk文件和config.json文件

## 目录结构

```
.
├── Core
│   ├── lpk_loader.py
│   └── utils.py
├── LpkUnpacker.py
├── README.md
├── output              <==
├── requirements.txt
└── lpkfolder           <==
    ├── target.lpk      <==
    └── config.json     <==
```

## 使用方法

1. clone这个仓库
2. 在仓库目录下新建output和lpkfolder两个文件夹
3. 把你的lpk和config.json丢到lpkfolder里去
4. 在仓库目录下运行```python LpkUnpacker.py -c lpkfolder/config.json lpkfolder/target.lpk output```

使用pycharm请自行搜索怎么添加python启动参数