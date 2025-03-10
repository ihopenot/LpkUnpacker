REM filepath: d:\Python_Project\LpkUnpackerGUI\start.bat
@echo off
setlocal enabledelayedexpansion

echo LPK Unpacker Launcher
echo LPK解包工具启动器
echo =============================
echo.

REM Check if input and output directories exist, create if not
if not exist "input" (
    echo Creating input directory...
    echo 正在创建input文件夹...
    mkdir "input"
    echo Please place your .lpk files and config.json in the input folder.
    echo 请将您的.lpk文件和config.json放入input文件夹中。
    pause
    exit /b
)

if not exist "output" (
    echo Creating output directory...
    echo 正在创建output文件夹...
    mkdir "output"
)

REM Count .lpk files in input directory
set lpk_count=0
for %%f in (input\*.lpk) do set /a lpk_count+=1

if %lpk_count% equ 0 (
    echo No .lpk files found in input directory.
    echo 在input文件夹中未找到.lpk文件。
    echo Please place your .lpk files in the input folder.
    echo 请将您的.lpk文件放入input文件夹中。
    pause
    exit /b
)

REM Check for config.json
set config_path=
if exist "input\config.json" (
    set config_path=input\config.json
) else (
    echo Config file not found in input directory. Will attempt to unpack without config.
    echo 在input文件夹中未找到config.json文件。将尝试不使用配置文件解包。
)

REM Process all .lpk files
echo Found %lpk_count% .lpk files to process.
echo 找到 %lpk_count% 个.lpk文件需要处理。
echo.

for %%f in (input\*.lpk) do (
    echo Processing: %%~nxf
    echo 正在处理: %%~nxf
    
    REM Run with Anaconda's base environment
    if not "!config_path!"=="" (
        echo Using config file: !config_path!
        echo 使用配置文件: !config_path!
        call conda run -n base python LpkUnpacker.py -c !config_path! "%%f" "output"
    ) else (
        call conda run -n base python LpkUnpacker.py "%%f" "output"
    )
    
    echo Finished processing %%~nxf
    echo 处理完成 %%~nxf
    echo.
)

echo All files processed! Results are in the output folder.
echo 所有文件处理完毕！结果保存在output文件夹中。
pause