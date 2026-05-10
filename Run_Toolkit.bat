@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
title FitGirl Repack Ultra Toolkit - FaicalOm_DZ

cd /d "%~dp0" || (
    echo [ERROR] Cannot enter toolkit folder.
    pause
    exit /b 1
)

cls
echo ================================================================
echo.
echo   FFFFF   AAAAA   IIIII  CCCCC   AAAAA  L       OOOOO  M   M
echo   F      A     A    I   C       A     A L      O     O MM MM
echo   FFFF   AAAAAAA    I   C       AAAAAAA L      O     O M M M
echo   F      A     A    I   C       A     A L      O     O M   M
echo   F      A     A  IIIII  CCCCC  A     A LLLLL   OOOOO  M   M
echo.
echo                         FaicalOm_DZ
echo                  FitGirl Repack Ultra Toolkit
echo ================================================================
echo.

echo [INFO] Working folder:
echo %CD%
echo.

for %%F in ("Page_Link_Extractor.py" "Direct_Link_Resolver.py" "Download_Manager_Sender.py") do (
    if not exist %%F (
        echo [ERROR] Missing required file: %%~F
        pause
        exit /b 1
    )
)

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PY=python"
    ) else (
        echo [ERROR] Python was not found in PATH.
        echo Install Python 3.10+ and add it to PATH.
        pause
        exit /b 1
    )
)

set "URL_FILE=%TEMP%\sdlt_url_%RANDOM%%RANDOM%.txt"
set "SOURCE_URL="
set /p "SOURCE_URL=Paste source page URL then press ENTER: "

if "%SOURCE_URL%"=="" (
    echo [ERROR] Empty URL.
    pause
    exit /b 1
)

> "%URL_FILE%" echo(%SOURCE_URL%

rem Clean previous generated files before starting a fresh run
del /q "source_links.txt" "source_manifest.txt" "fuckingfast_links.txt" "fuckingfast_manifest.txt" >nul 2>nul
del /q "real_direct_links.txt" "resolved_manifest.txt" "resolved_map_debug.txt" "failed_links.txt" >nul 2>nul
del /q "selected_links.txt" "روابط_نهائية.txt" "debug_*.html" "debug_*.png" >nul 2>nul

echo.
echo ================================================================
echo [1/3] Extracting source links
echo ================================================================
%PY% -u "Page_Link_Extractor.py" < "%URL_FILE%"
set "STEP1=%ERRORLEVEL%"
del "%URL_FILE%" >nul 2>nul

if not "%STEP1%"=="0" (
    echo.
    echo [ERROR] Stage 1 failed.
    pause
    exit /b 1
)

if not exist "source_links.txt" if not exist "fuckingfast_links.txt" (
    echo [ERROR] No source links file was created.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo [2/3] Resolving direct links
echo ================================================================
%PY% -u "Direct_Link_Resolver.py"
if errorlevel 1 (
    echo.
    echo [ERROR] Stage 2 failed.
    pause
    exit /b 1
)

if not exist "resolved_map_debug.txt" (
    echo [ERROR] resolved_map_debug.txt was not created.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo [3/3] Choose files and send to download manager
echo ================================================================
%PY% -u "Download_Manager_Sender.py"
if errorlevel 1 (
    echo.
    echo [ERROR] Stage 3 failed.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo Done. Thank you for using FaicalOm_DZ Toolkit.
echo ================================================================
pause
exit /b 0
