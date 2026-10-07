@echo off
title CloudFlow AI Setup and Server
cd /d "%~dp0"
if not exist venv (
  echo Creating Python virtual environment...
  py -3.10 -m venv venv
)
call venv\Scripts\activate
echo Installing required packages...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo CloudFlow AI is starting at http://127.0.0.1:5000
echo Admin login: admin@cloudflow.local / admin123
echo User login:  user@cloudflow.local / user123
echo.
python app.py
pause

