@echo off

cd /d "C:\Program Files\AGHIMS-begoro\backend"

echo ======================================== >> logs\backend.log
echo Starting backend at %date% %time% >> logs\backend.log

"C:\Program Files\AGHIMS-begoro\backend\venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> logs\backend.log 2>&1

echo Backend stopped at %date% %time% >> logs\backend.log