# LpkUnpacker
[English](https://github.com/ihopenot/LpkUnpacker/blob/master/README_en.md)/中文

这个工具用来解包Live2dViewerEx的LPK文件

如果你在使用工具时遇到任何困难，请先查询'[Issues](https://github.com/ihopenot/LpkUnpacker/issues)'中的内容

*增加了对STD_1_0以及之前的格式支持
注意，少部分的早期lpk仍然无法解包，推测可能存在未知的密钥生成或解密算法

## 使用说明

### 方法一：使用已编译的EXE文件（推荐）

1. 从[Releases](https://github.com/Moeary/LpkUnpackerGUI/releases/tag/Gold)页面下载最新的LpkUnpackerGUI.exe文件
2. 双击运行LpkUnpackerGUI.exe
3. 在界面中选择要解包的LPK文件、对应的config.json文件（或者拖动也行）以及输出目录(默认输出为exe程序目录下output文件夹)
4. 点击"Extract"按钮开始解包过程

![Guide Animation](Img/Guide.gif)

### 方法二：从源码运行

如果你希望从源码运行，请按照以下步骤操作：

1. 安装依赖
```
python -m pip install -r requirements.txt
```

2. 运行程序

如果你需要使用GUI版本，使用如下的命令：

```
python LpkUnpackerGUI.py
```

如果你需要使用命令行解包，可以使用以下命令:
```
python LpkUnpacker.py <args>
```

LpkUnpacker.py的参数说明如下所示：

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

## 编译

release中的版本使用nuitka编译，如果你希望自行编译可执行文件，可以使用提供的编译脚本：

1. 确保已安装所有依赖：
   ```
   pip install -r requirements.txt
   pip install nuitka
   ```
   
2. 运行编译脚本：
   ```
   compile.bat
   ```

编译好的可执行文件将保存在build目录中。

## 注意

Steam创意工坊中的lpk文件通常需要config.json来解密

.lpk文件通常在下面这样的路径下

`path/to/your/steam/steamapps/workshop/content/616720/...` 或者 `path/to/your/steam/steamapps/common/Live2DViewerEX/shared/workshop/...`

如果要解密wpk文件，你需要先把它解压之后得到lpk文件和config.json文件

## 目前功能

- [✓] 解包Lpk文件GUI界面

## TOLIST
- [ ] Wpk文件支持
- [ ] 软件直接预览Live2d文件,By live2d-py库
- [ ] 直接解包游戏live2d文件,By Unitypy/AssetStudio Cli
- [ ] 分图层导出psd格式文件,方便魔改

<!-- ## 目录结构

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

使用pycharm请自行搜索怎么添加python启动参数 -->