@echo off
setlocal
REM ===== LpkUnpackerGUI Compiler =====
echo ===== LpkUnpackerGUI Compiler =====
echo Starting compilation process...

set "SCRIPT_DIR=%~dp0"
set "RUN_PY="
set "RUN_PY_IS_CMD=0"
set "DESC="
set "CONSOLE_MODE=disable"

REM Enable console when DEBUG=1 for troubleshooting black screen
if /I "%DEBUG%"=="1" (
    set "CONSOLE_MODE=attach"
    set "QT_DEBUG_PLUGINS=1"
)

set "RUN_PY=python"
set "RUN_PY_IS_CMD=0"
set "DESC=Global Python"

echo Using Python: %DESC%

REM Basic check: Python availability
%RUN_PY% -V >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Selected Python command failed: %RUN_PY%
    exit /b 1
)

REM Check Nuitka is installed in the selected environment
%RUN_PY% -c "import nuitka" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Nuitka not found in the selected environment.
    echo Please install Nuitka:
    echo - Conda:   conda install -n %ENV_NAME% -c conda-forge nuitka
    echo - venv:    %ENV_NAME%\Scripts\pip install nuitka
    echo - global:  pip install nuitka
    exit /b 1
)

REM Ensure websockets and requests are installed (as per runtime requirements)
%RUN_PY% -c "import websockets, requests" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Missing packages detected. Installing: websockets, requests
    %RUN_PY% -m pip install websockets requests
)

echo Compiling application with Nuitka using %DESC%...
echo This may take several minutes. Please be patient...

REM Main compilation command
if "%RUN_PY_IS_CMD%"=="0" (
    %RUN_PY% -m nuitka --onefile ^
        --enable-plugin=pyqt5 ^
        --output-dir=build ^
        --windows-console-mode=%CONSOLE_MODE% ^
        --jobs=%NUMBER_OF_PROCESSORS% ^
        --lto=no ^
        --show-progress ^
        --include-data-dir=./GUI/assets=GUI/assets ^
        --include-data-dir=./Img=Img ^
        --windows-icon-from-ico=Img/icon.ico ^
        --nofollow-import-to=matplotlib,scipy,pandas,tkinter ^
        --python-flag=no_site ^
        --python-flag=no_docstrings ^
        LpkUnpackerGUI.py
)

if %ERRORLEVEL% neq 0 (
    echo Compilation failed with error code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

echo.
echo Compilation completed successfully!
echo Executable can be found in the 'build' directory.
echo.
