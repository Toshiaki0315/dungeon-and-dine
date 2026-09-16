@echo off
rem 手元でテストプレイするための起動スクリプト（Windows）。
rem 使い方:
rem   run.bat                起動する
rem   run.bat --seed 123     起動引数はそのまま main.py に渡す
setlocal
cd /d "%~dp0"

set PYTHON=.venv\Scripts\python.exe
if not exist "%PYTHON%" (
  echo 仮想環境が見つかりません。先にセットアップしてください:
  echo   uv venv --python 3.11 .venv
  echo   uv pip install --python .venv\Scripts\python.exe -r requirements.txt
  exit /b 1
)

"%PYTHON%" main.py %*
endlocal
