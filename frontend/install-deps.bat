@echo off
cd /d "%~dp0"
echo Installing frontend dependencies...
call npm install
echo Done. Run: npm run dev
pause
