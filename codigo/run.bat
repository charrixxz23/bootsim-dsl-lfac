@echo off
rem ejecuta bootsim dsl desde cmd: run.bat archivo.dsl [--debug]
where python >nul 2>nul
if %errorlevel%==0 (
  python "%~dp0main.py" %*
) else (
  py -3 "%~dp0main.py" %*
)
exit /b %errorlevel%
