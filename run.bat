@echo off
REM Chay tren Windows, khong can make:
REM   run.bat              -^> cai dat (lan dau) + chay demo
REM   run.bat "cau hoi"    -^> hoi 1 cau tuy y
REM   run.bat eval         -^> cham diem testset (hybrid va dense)
if not exist .venv python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
if not exist .env (
    copy .env.example .env
    echo Da tao file .env. Mo file .env, dien GROQ_API_KEY roi chay lai run.bat
    exit /b
)
if /I "%~1"=="eval" (
    .venv\Scripts\python -m tests.eval hybrid
    .venv\Scripts\python -m tests.eval dense
    exit /b
)
.venv\Scripts\python demo.py %*