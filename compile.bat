@echo off
setlocal
REM ===== LpkUnpackerGUI Compiler =====
echo ===== LpkUnpackerGUI Compiler =====
echo Starting compilation process...

REM ---------------------------------
REM Configuration: hardcoded environment name
REM Change ENV_NAME to your venv/conda environment name.
REM Resolution order:
REM 1) Local venv at root: %~dp0<ENV_NAME>\Scripts\python.exe
REM 2) Conda env with the same name (if Conda exists)
REM 3) Global Python
REM ---------------------------------
set "ENV_NAME=venv"

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

REM Prefer currently active Conda environment if available
if defined CONDA_PREFIX (
    set "RUN_PY=python"
    set "RUN_PY_IS_CMD=0"
    set "DESC=Active Conda env '%CONDA_DEFAULT_ENV%'"
    goto SELECTED
)

REM Try local venv first
set "VENV_PY=%SCRIPT_DIR%%ENV_NAME%\Scripts\python.exe"
if exist "%VENV_PY%" (
    set "RUN_PY=%VENV_PY%"
    set "RUN_PY_IS_CMD=0"
    set "DESC=Local venv '%ENV_NAME%'"
    goto SELECTED
)

REM Try Conda env if available
set "CONDA_CMD="
if defined CONDA_EXE (
    set "CONDA_CMD=%CONDA_EXE%"
) else (
    where conda >nul 2>&1
    if %ERRORLEVEL%==0 (
        set "CONDA_CMD=conda"
    ) else (
        where conda.bat >nul 2>&1
        if %ERRORLEVEL%==0 (
            set "CONDA_CMD=conda.bat"
        )
    )
)

if defined CONDA_CMD (
    %CONDA_CMD% run --no-capture-output -n %ENV_NAME% python -V >nul 2>&1
    if %ERRORLEVEL%==0 (
        set "RUN_PY=%CONDA_CMD% run --no-capture-output -n %ENV_NAME% python"
        set "RUN_PY_IS_CMD=1"
        set "DESC=Conda env '%ENV_NAME%'"
        goto SELECTED
    )
)

REM Fallback to global Python
set "RUN_PY=python"
set "RUN_PY_IS_CMD=0"
set "DESC=Global Python"

:SELECTED

echo Using Python: %DESC%

REM Basic check: Python availability
if "%RUN_PY_IS_CMD%"=="0" (
    "%RUN_PY%" -V >nul 2>&1
) else (
    %RUN_PY% -V >nul 2>&1
)
if %ERRORLEVEL% neq 0 (
    echo Error: Selected Python command failed: %RUN_PY%
    pause
    exit /b 1
)

REM Check Nuitka is installed in the selected environment
if "%RUN_PY_IS_CMD%"=="0" (
    "%RUN_PY%" -c "import nuitka" >nul 2>&1
) else (
    %RUN_PY% -c "import nuitka" >nul 2>&1
)
if %ERRORLEVEL% neq 0 (
    echo Error: Nuitka not found in the selected environment.
    echo Please install Nuitka:
    echo - Conda:   conda install -n %ENV_NAME% -c conda-forge nuitka
    echo - venv:    %ENV_NAME%\Scripts\pip install nuitka
    echo - global:  pip install nuitka
    pause
    exit /b 1
)

REM Ensure websockets and requests are installed (as per runtime requirements)
if "%RUN_PY_IS_CMD%"=="0" (
    "%RUN_PY%" -c "import websockets, requests" >nul 2>&1
) else (
    %RUN_PY% -c "import websockets, requests" >nul 2>&1
)
if %ERRORLEVEL% neq 0 (
    echo Missing packages detected. Installing: websockets, requests
    if "%RUN_PY_IS_CMD%"=="0" (
        "%RUN_PY%" -m pip install websockets requests
    ) else (
        %RUN_PY% -m pip install websockets requests
    )
)

echo Compiling application with Nuitka using %DESC%...
echo This may take several minutes. Please be patient...

REM Main compilation command
if "%RUN_PY_IS_CMD%"=="0" (
    "%RUN_PY%" -m nuitka --onefile ^
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
) else (
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
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Compilation completed successfully!
echo Executable can be found in the 'build' directory.
echo.

pause