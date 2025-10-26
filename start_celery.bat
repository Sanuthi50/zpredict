@echo off
echo Starting Celery Worker for ZPredict...
cd /d "c:\Sanuthi BSC\Sem 3\Zpredict\zpredict"

:start
echo [%date% %time%] Starting Celery worker...
celery -A zpredict worker --loglevel=info --concurrency=2 --pool=solo
echo [%date% %time%] Celery worker stopped. Restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto start
