@echo off
REM Cho phep go "make setup", "make demo", "make eval" tren Windows (cmd) khi may khong cai make.
REM Tuong duong voi Makefile (dung cho Linux/macOS).
if /I "%~1"=="setup" goto setup
if /I "%~1"=="demo" goto demo
if /I "%~1"=="eval" goto eval
echo Cach dung: make setup ^| make demo ^| make demo "cau hoi" ^| make eval
exit /b 1

:setup
if not exist .venv python -m venv .venv
if errorlevel 1 exit /b 1
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
if not exist .env copy .env.example .env
echo Da cai xong. Mo file .env va dien GROQ_API_KEY truoc khi chay demo.
exit /b 0

:demo
.venv\Scripts\python demo.py %2
exit /b %errorlevel%

:eval
.venv\Scripts\python -m tests.eval hybrid
.venv\Scripts\python -m tests.eval dense
exit /b %errorlevel%
