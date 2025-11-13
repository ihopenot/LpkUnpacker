@echo off
REM filepath: d:\Python_Project\LpkUnpackerGUI\compile.bat
echo ===== LpkUnpackerGUI Compiler =====
echo Starting compilation process...

@REM REM Activate Conda base environment
@REM echo Activating Conda base environment...
@REM call conda activate base
@REM if %ERRORLEVEL% neq 0 (
@REM     echo Error: Failed to activate Conda base environment!
@REM     echo Make sure Conda is properly installed and initialized.
@REM     pause
@REM     exit /b 1
@REM )

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python not found!
    pause
    exit /b 1
)

REM Check if nuitka is installed
python -c "import nuitka" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Nuitka not found.
    pause
    exit /b 1
    @REM echo Warning: Nuitka not found. Attempting to install it...
    @REM conda install -c conda-forge nuitka -y
    @REM if %ERRORLEVEL% neq 0 (
    @REM     echo Failed to install Nuitka through Conda. Trying pip...
    @REM     pip install nuitka
    @REM     if %ERRORLEVEL% neq 0 (
    @REM         echo Failed to install Nuitka. Aborting compilation.
    @REM         pause
    @REM         exit /b 1
    @REM     )
    @REM )
)

echo Compiling application with Nuitka...
echo This may take several minutes. Please be patient...

REM Main compilation command
python -m nuitka --onefile ^
    --enable-plugin=pyqt5 ^
    --output-dir=build ^
    --windows-console-mode=disable ^
    --include-data-dir=./GUI/assets=GUI/assets ^
    --include-data-dir=./Img=Img ^
    --include-package=qfluentwidgets,filetype,live2d,numpy,fastapi,uvicorn,starlette ^
    --windows-icon-from-ico=Img/icon.ico ^
    --nofollow-import-to=matplotlib,scipy,pandas,tkinter,PyQtWebEngine,PyQt5.QtWebEngineWidgets,PyQt5.QtWebEngineCore ^
    --python-flag=no_site ^
    --python-flag=no_docstrings ^
    --remove-output ^
    LpkUnpackerGUI.py

if %ERRORLEVEL% neq 0 (
    echo Compilation failed with error code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Compilation completed successfully!
echo Executable can be found in the 'build' directory.
echo.

pause