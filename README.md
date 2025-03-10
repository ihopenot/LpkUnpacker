# LpkUnpacker GUI

原仓库[在这](https://github.com/ihopenot/LpkUnpacker),使用python对大部分人来说还是太困难了,因此我做了一个GUI工具,用来解包Live2dViewerEx加密的LPK文件,并将其还原成其他软件/引擎可以识别的正常live2d格式文件

如果你在使用工具时遇到任何困难，请先查询'[Issues](https://github.com/ihopenot/LpkUnpacker/issues)'中的内容

## 使用方法

### 方法一：使用已编译的EXE文件（推荐）

1. 从[Releases](https://github.com/Moeary/LpkUnpackerGUI/releases/tag/Gold)页面下载最新的LpkUnpackerGUI.exe文件
2. 双击运行LpkUnpackerGUI.exe
3. 在界面中选择要解包的LPK文件、对应的config.json文件（或者拖动也行）以及输出目录(默认输出为exe程序目录下output文件夹)
4. 点击"Extract"按钮开始解包过程

![Guide Animation](Img/Guide.gif)

### 方法二：从源码运行

如果你希望从源码运行，请按照以下步骤操作：

1. 克隆或下载此仓库
2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```
3. 运行主程序：
   ```
   python LpkUnpackerGUI.py
   ```

## 从源码编译

如果你希望自行编译EXE文件，可以使用提供的编译脚本：

1. 确保已安装所有依赖：
   ```
   pip install -r requirements.txt
   pip install nuitka
   ```
   
2. 运行编译脚本：
   ```
   compile.bat
   ```

编译好的EXE文件将保存在build目录中。

## 目前功能

- [✓] 解包Lpk文件GUI界面

## TOLIST
- [ ] Wpk文件支持
- [ ] 软件直接预览Live2d文件,By live2d-py库
- [ ] 直接解包游戏live2d文件,By Unitypy/AssetStudio Cli
- [ ] 分图层导出psd格式文件,方便魔改