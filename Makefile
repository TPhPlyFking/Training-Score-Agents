ifeq ($(OS),Windows_NT)
PY = ".venv\Scripts\python.exe"
SYS_PY = python
else
PY = .venv/bin/python
SYS_PY = python3
endif

setup:
	$(SYS_PY) -c "import os, venv; os.path.isdir('.venv') or venv.create('.venv', with_pip=True)"
	$(PY) -m pip install -r requirements.txt
	$(PY) -c "import os, shutil; os.path.exists('.env') or shutil.copy('.env.example', '.env')"
	@echo Da cai xong. Mo file .env va dien GROQ_API_KEY truoc khi chay demo.

demo:
	$(PY) demo.py

eval:
	$(PY) -m tests.eval hybrid
	$(PY) -m tests.eval dense