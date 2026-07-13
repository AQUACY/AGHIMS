@echo off

cd /d "C:\Program Files\AGHIMS-begoro\frontend"

echo ======================================== >> logs\frontend.log
echo Starting backend at %date% %time% >> logs\frontend.log

"C:\Program Files\nodejs\npm.cmd" run dev >> logs\frontend.log 2>&1

echo Frontend stopped at %date% %time% >> logs\frontend.log