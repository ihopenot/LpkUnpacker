@echo off
REM filepath: d:\Python_Project\LpkUnpackerGUI\compile.bat
echo ===== LpkUnpackerGUI Compiler =====
echo Starting compilation process...

REM Activate Conda base environment
echo Activating Conda base environment...
call conda activate base
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to activate Conda base environment!
    echo Make sure Conda is properly installed and initialized.
    pause
    exit /b 1
)

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python not found in Conda environment!
    pause
    exit /b 1
)

REM Check if nuitka is installed
python -c "import nuitka" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Warning: Nuitka not found. Attempting to install it...
    conda install -c conda-forge nuitka -y
    if %ERRORLEVEL% neq 0 (
        echo Failed to install Nuitka through Conda. Trying pip...
        pip install nuitka
        if %ERRORLEVEL% neq 0 (
            echo Failed to install Nuitka. Aborting compilation.
            pause
            exit /b 1
        )
    )
)

echo Compiling application with Nuitka in Conda base environment...
echo This may take several minutes. Please be patient...

REM Main compilation command
python -m nuitka --onefile ^
    --enable-plugin=pyqt5 ^
    --output-dir=build ^
    --windows-disable-console ^
    --include-data-dir=./Img=Img ^
    --include-package=qfluentwidgets ^
    --include-package=filetype ^
    --windows-icon-from-ico=Img/icon.ico ^
    --nofollow-import-to=numpy,matplotlib,scipy,pandas,tkinter ^
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